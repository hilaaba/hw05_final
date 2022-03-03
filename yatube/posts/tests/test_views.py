import shutil
import tempfile

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..models import Follow, Group, Post
from ..views import POSTS_COUNT_PER_PAGE

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)

User = get_user_model()


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostPageTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='author')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test_slug',
            description='Тестовое описание группы',
        )
        cls.small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        cls.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=cls.small_gif,
            content_type='image/gif',
        )
        cls.post = Post.objects.create(
            author=cls.author,
            group=cls.group,
            text='Тестовый пост',
            image=cls.uploaded,
        )
        cls.comment = cls.post.comments.create(
            author=cls.author,
            text='Тестовый комментарий',
        )
        cls.new_group = Group.objects.create(
            title='Новая тестовая группа',
            slug='test_new_slug',
            description='Тестовое описание новой группы',
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.guest_client = Client()
        self.user = User.objects.create_user(username='HasNoName')
        self.user_client = Client()
        self.user_client.force_login(self.user)
        self.author_client = Client()
        self.author_client.force_login(self.author)
        Follow.objects.create(user=self.user, author=self.author)
        self.not_follower = User.objects.create_user(username='NotFollower')
        self.not_follower_client = Client()
        self.not_follower_client.force_login(self.not_follower)

    def test_pages_uses_correct_template(self):
        """
        URL-адрес использует соответствующий шаблон для
        авторизованного пользователя.
        """
        self.user_post = Post.objects.create(
            author=self.user,
            text='Тестовый пост от user',
        )
        templates_pages_names = {
            reverse('posts:index'):
                'posts/index.html',
            reverse('posts:group_posts', kwargs={'slug': self.group.slug}):
                'posts/group_list.html',
            reverse(
                'posts:profile', kwargs={'username': self.author.username}
            ):
                'posts/profile.html',
            reverse('posts:post_detail', kwargs={'post_id': self.post.id}):
                'posts/post_detail.html',
            reverse('posts:post_create'):
                'posts/create_post.html',
            reverse('posts:post_edit', kwargs={'post_id': self.user_post.id}):
                'posts/create_post.html',
            reverse('posts:follow_index'): 'posts/follow.html',
        }
        for reverse_name, template in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.user_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_page_correct_page_obj_context(self):
        """
        Шаблоны:
            1. index
            2. group_posts
            3. profile
            4. follow_index
        сформированы с правильным page_obj контекстом.
        """
        reverse_names = (
            reverse('posts:index'),
            reverse('posts:group_posts', kwargs={'slug': self.group.slug}),
            reverse(
                'posts:profile', kwargs={'username': self.author.username}
            ),
            reverse('posts:follow_index')
        )
        for reverse_name in reverse_names:
            with self.subTest(reverse_name=reverse_name):
                response = self.user_client.get(reverse_name)
                post = response.context['page_obj'][0]
                self.assertEqual(post.author, self.author)
                self.assertEqual(post.text, self.post.text)
                self.assertEqual(post.group.slug, self.group.slug)
                self.assertEqual(post.image, self.post.image)

    def test_page_correct_posts_count_context(self):
        """
        Шаблоны:
            1. profile
            2. post_detail
        сформированы с правильным posts_count контекстом.
        """
        reverse_names = {
            reverse(
                'posts:profile', kwargs={'username': self.author.username}
            ):
                Post.objects.filter(author=self.author).count(),
            reverse(
                'posts:post_detail', kwargs={'post_id': self.post.id}
            ):
                Post.objects.filter(author=self.post.author).count(),
        }
        for reverse_name, posts_count in reverse_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.user_client.get(reverse_name)
                self.assertEqual(response.context['posts_count'], posts_count)

    def test_group_posts_correct_context(self):
        """
        Шаблон group_posts сформирован с правильным контекстом.
        """
        response = self.user_client.get(
            reverse('posts:group_posts', kwargs={'slug': self.group.slug})
        )
        group = response.context['group']
        group_title = group.title
        group_description = group.description
        self.assertEqual(group_title, self.group.title)
        self.assertEqual(group_description, self.group.description)

    def test_profile_posts_correct_context(self):
        """
        Шаблон profile сформирован с правильным контекстом.
        """
        response = self.user_client.get(
            reverse('posts:profile', kwargs={'username': self.author.username})
        )
        self.assertEqual(response.context['author'], self.author)
        self.assertTrue(response.context['following'])

    def test_post_detail_correct_context(self):
        """
        Шаблон post_detail сформирован с правильным контекстом.
        """
        response = self.user_client.get(
            reverse('posts:post_detail', kwargs={'post_id': self.post.id})
        )
        post = response.context['post']
        self.assertEqual(post.author.username, self.author.username)
        self.assertEqual(post.text, self.post.text)
        self.assertEqual(post.image, self.post.image)
        form_field = response.context.get('form').fields.get('text')
        self.assertIsInstance(form_field, forms.fields.CharField)
        self.assertIn(self.comment, response.context['comments'])

    def test_new_post_create_and_post_edit_page_correct_context(self):
        """
        Шаблоны:
            1. create
            2. post_edit
        сформированы с правильным контекстом.
        """
        reverse_names = {
            reverse('posts:post_create'): False,
            reverse('posts:post_edit', kwargs={'post_id': self.post.id}): True,
        }
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        for reverse_name, is_edit in reverse_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.author_client.get(reverse_name)
                for value, expected in form_fields.items():
                    with self.subTest(value=value):
                        form_field = (
                            response.context.get('form').fields.get(value)
                        )
                        self.assertIsInstance(form_field, expected)
                self.assertEqual(response.context['is_edit'], is_edit)

    def test_new_post_exist_on_page(self):
        """
        Проверка на добавление нового поста от автора на страницы:
            1. index
            2. group_posts
            3. profile author
            4. follow_index для user
        """
        self.new_post = Post.objects.create(
            author=self.author,
            group=self.new_group,
            text='Новый тестовый пост',
        )
        reverse_names = (
            reverse('posts:index'),
            reverse('posts:group_posts', kwargs={'slug': self.new_group.slug}),
            reverse(
                'posts:profile',
                kwargs={'username': self.author.username},
            ),
            reverse('posts:follow_index'),
        )
        for reverse_name in reverse_names:
            with self.subTest(reverse_name=reverse_name):
                response = self.user_client.get(reverse_name)
                self.assertIn(self.new_post, response.context['page_obj'])

    def test_new_post_not_exist_on_another_page(self):
        """
        Проверка на то, что новый пост не добавляется на странице:
            1. другой группы group_posts
            2. другого пользователя profile user
            3. follow_index для пользователя not_follower
        """
        self.new_post = Post.objects.create(
            author=self.author,
            group=self.new_group,
            text='Новый тестовый пост',
        )
        reverse_names = (
            reverse('posts:group_posts', kwargs={'slug': self.group.slug}),
            reverse(
                'posts:profile', kwargs={'username': self.user.username}
            ),
            reverse('posts:follow_index'),
        )
        for reverse_name in reverse_names:
            with self.subTest(reverse_name=reverse_name):
                response = self.not_follower_client.get(reverse_name)
                self.assertNotIn(self.new_post, response.context['page_obj'])

    def test_cache_index_page(self):
        """
        Проверка кеширования шаблона index.
        """
        cache.clear()
        response = self.user_client.get(reverse('posts:index'))
        cache_check = response.content
        post = Post.objects.get(pk=self.post.id)
        post.delete()
        response = self.user_client.get(reverse('posts:index'))
        self.assertEqual(response.content, cache_check)
        cache.clear()
        response = self.user_client.get(reverse('posts:index'))
        self.assertNotEqual(response.content, cache_check)

    def test_profile_follow(self):
        """
        Авторизованный пользователь может подписываться
        на других пользователей.
        """
        author_follower_count = (
            Follow.objects.filter(author=self.author).count()
        )
        self.new_user = User.objects.create_user(username='NewUser')
        self.new_user_client = Client()
        self.new_user_client.force_login(self.not_follower)
        Follow.objects.create(user=self.new_user, author=self.author)
        self.assertEqual(
            Follow.objects.filter(author=self.author).count(),
            author_follower_count + 1,
        )
        response = self.new_user_client.get(
            reverse(
                'posts:profile_follow',
                kwargs={'username': self.author.username},
            ),
        )
        excepted_value = reverse(
            'posts:profile',
            kwargs={'username': self.author.username},
        )
        self.assertRedirects(response, excepted_value)

    def test_profile_unfollow(self):
        """
        Авторизованный пользователь может отписываться от других пользователей.
        """
        author_follower_count = (
            Follow.objects.filter(author=self.author).count()
        )
        Follow.objects.filter(user=self.user, author=self.author).delete()
        self.assertEqual(
            Follow.objects.filter(author=self.author).count(),
            author_follower_count - 1,
        )
        response = self.user_client.get(
            reverse(
                'posts:profile_unfollow',
                kwargs={'username': self.author.username},
            ),
        )
        excepted_value = reverse(
            'posts:profile',
            kwargs={'username': self.author.username},
        )
        self.assertRedirects(response, excepted_value)


class PaginatorViewsTest(TestCase):
    """
    Проверка паджинатора в шаблонах:
        1. index
        2. group_posts
        3. profile
        4. follow_index
    """
    POSTS_COUNT = 13

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='author')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test_slug',
            description='Тестовое описание группы',
        )
        posts = (
            Post(
                author=cls.author,
                group=cls.group,
                text=f'Тестовый пост {number}'
            ) for number in range(cls.POSTS_COUNT)
        )
        Post.objects.bulk_create(posts)

    def setUp(self):
        self.user = User.objects.create_user(username='HasNoName')
        self.user_client = Client()
        self.user_client.force_login(self.user)
        Follow.objects.create(
            user=self.user,
            author=self.author,
        )
        self.reverse_names = (
            reverse('posts:index'),
            reverse('posts:group_posts', kwargs={'slug': self.group.slug}),
            reverse(
                'posts:profile', kwargs={'username': self.author.username}
            ),
            reverse('posts:follow_index')
        )

    def test_first_page_contains_ten_records(self):
        for reverse_name in self.reverse_names:
            with self.subTest(reverse_name=reverse_name):
                response_first_page = self.user_client.get(reverse_name)
                self.assertEqual(
                    len(response_first_page.context['page_obj']),
                    POSTS_COUNT_PER_PAGE,
                )

    def test_second_page_contains_three_records(self):
        for reverse_name in self.reverse_names:
            with self.subTest(reverse_name=reverse_name):
                response_second_page = self.user_client.get(
                    reverse_name, {'page': '2'}
                )
                self.assertEqual(
                    len(response_second_page.context['page_obj']),
                    self.POSTS_COUNT % POSTS_COUNT_PER_PAGE,
                )
