import shutil
import tempfile
from http import HTTPStatus

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.models.fields.files import ImageFieldFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..forms import PostForm
from ..models import Group, Post

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)

User = get_user_model()


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostFormTests(TestCase):
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
        cls.form = PostForm()

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

    def test_create_post(self):
        """
        Валидная форма создает запись в Post.
        """
        posts_count = Post.objects.count()
        new_uploaded = SimpleUploadedFile(
            name='new_small.gif',
            content=self.small_gif,
            content_type='image/gif',
        )
        form_data = {
            'author': self.user,
            'text': 'Тестовый текст',
            'group': self.group.pk,
            'image': new_uploaded,
        }
        response = self.user_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True,
        )
        self.assertRedirects(
            response,
            reverse('posts:profile', kwargs={'username': self.user.username}),
        )
        self.assertEqual(Post.objects.count(), posts_count + 1)
        last_post = Post.objects.first()
        self.assertEqual(last_post.author, form_data['author'])
        self.assertEqual(last_post.text, form_data['text'])
        self.assertEqual(last_post.group.pk, form_data['group'])
        self.assertIsInstance(last_post.image, ImageFieldFile)
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_edit_post(self):
        """
        Валидная форма изменяет запись в Post.
        """
        posts_count = Post.objects.count()
        self.new_group = Group.objects.create(
            title='Новая тестовая группа',
            slug='new_test_slug',
            description='Новое тестовое описание группы',
        )
        modified_uploaded = SimpleUploadedFile(
            name='modified_small.gif',
            content=self.small_gif,
            content_type='image/gif',
        )
        form_data = {
            'author': self.author,
            'text': 'Измененный тестовый текст',
            'group': self.new_group.pk,
            'image': modified_uploaded,
        }
        response = self.author_client.post(
            reverse(
                'posts:post_edit',
                kwargs={'post_id': self.post.id},
            ),
            data=form_data,
            follow=True,
        )
        self.assertRedirects(
            response,
            reverse(
                'posts:post_detail',
                kwargs={'post_id': self.post.id}),
        )
        self.assertEqual(Post.objects.count(), posts_count)
        modified_post = Post.objects.get(pk=self.post.id)
        self.assertEqual(modified_post.author, form_data['author'])
        self.assertEqual(modified_post.text, form_data['text'])
        self.assertEqual(modified_post.group.pk, form_data['group'])
        self.assertIsInstance(modified_post.image, ImageFieldFile)
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_add_comment(self):
        """
        Валидная форма создает комментарий к посту.
        """
        post = Post.objects.get(pk=self.post.id)
        comments_count = post.comments.count()
        form_data = {
            'author': self.user,
            'text': 'Новый тестовый комментарий',
        }
        response = self.user_client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.id}),
            data=form_data,
            follow=True,
        )
        self.assertRedirects(
            response,
            reverse('posts:post_detail', kwargs={'post_id': self.post.id}),
        )
        self.assertEqual(post.comments.count(), comments_count + 1)
        last_comment = post.comments.last()
        self.assertEqual(last_comment.author, form_data['author'])
        self.assertEqual(last_comment.text, form_data['text'])
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_anonymous_cannot_add_comment(self):
        """
        Неавторизованный пользователь не может оставить комментарий к посту.
        """
        comments_count = self.post.comments.count()
        form_data = {
            'text': 'Комментарий от анонима',
        }
        self.guest_client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.id}),
            data=form_data,
            follow=True,
        )
        self.assertEqual(comments_count, self.post.comments.count())
