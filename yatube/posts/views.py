from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import (
    get_list_or_404, get_object_or_404, redirect, render
)

from .forms import CommentForm, PostForm
from .models import Follow, Group, Post, User

POSTS_COUNT_PER_PAGE = 10


def get_page_obj(request, posts):
    paginator = Paginator(posts, POSTS_COUNT_PER_PAGE)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return page_obj


def index(request):
    posts = Post.objects.all()
    context = {
        'page_obj': get_page_obj(request, posts),
    }
    return render(request, 'posts/index.html', context)


def group_posts(request, slug):
    group = get_object_or_404(Group, slug=slug)
    posts = get_list_or_404(Post, group=group)
    context = {
        'group': group,
        'page_obj': get_page_obj(request, posts),
    }
    return render(request, 'posts/group_list.html', context)


def profile(request, username):
    author = get_object_or_404(User, username=username)
    posts = author.posts.all()
    posts_count = posts.count()
    following = (
        request.user.is_authenticated and
        Follow.objects.filter(user=request.user, author=author)
    )
    context = {
        'page_obj': get_page_obj(request, posts),
        'author': author,
        'posts_count': posts_count,
        'following': following,
    }
    return render(request, 'posts/profile.html', context)


def post_detail(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    posts_count = post.author.posts.count()
    form = CommentForm()
    comments = post.comments.all()
    context = {
        'post': post,
        'posts_count': posts_count,
        'form': form,
        'comments': comments,
    }
    return render(request, 'posts/post_detail.html', context)


@login_required
def post_create(request):
    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
    )
    if form.is_valid():
        form.instance.author = request.user
        form.save()
        return redirect('posts:profile', username=request.user)
    context = {
        'form': form,
        'is_edit': False,
    }
    return render(request, 'posts/create_post.html', context)


@login_required
def post_edit(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    if request.user != post.author:
        return redirect('posts:post_detail', post_id=post_id)
    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
        instance=post,
    )
    if form.is_valid():
        form.save()
        return redirect('posts:post_detail', post_id=post_id)
    context = {
        'form': form,
        'is_edit': True,
    }
    return render(request, 'posts/create_post.html', context)


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('posts:post_detail', post_id=post_id)


@login_required
def follow_index(request):
    posts = Post.objects.filter(author__following__user=request.user)
    context = {
        'page_obj': get_page_obj(request, posts),
        'follow': True,
    }
    return render(request, 'posts/follow.html', context)


@login_required
def profile_follow(request, username):
    follow = get_object_or_404(User, username=username)
    is_exist = Follow.objects.filter(user=request.user, author=follow).exists()
    if follow != request.user and not is_exist:
        Follow.objects.get_or_create(
            user=request.user,
            author=follow,
        )
    return redirect('posts:profile', username=username)


@login_required
def profile_unfollow(request, username):
    unfollow = get_object_or_404(User, username=username)
    Follow.objects.filter(user=request.user, author=unfollow).delete()
    return redirect('posts:profile', username=username)
