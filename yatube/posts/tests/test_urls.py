from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from ..models import Group, Post

User = get_user_model()


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='author')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test_slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.author,
            group=cls.group,
            text='Тестовый пост',
        )

    def setUp(self):
        self.guest_client = Client()
        self.user = User.objects.create_user(username='HasNoName')
        self.user_client = Client()
        self.user_client.force_login(self.user)
        self.author_client = Client()
        self.author_client.force_login(self.author)

    def test_urls_exists_at_desired_location(self):
        """
        Страница доступна любому пользователю.
        """
        reverse_names = (
            reverse('posts:index'),
            reverse('posts:group_posts', kwargs={'slug': self.group.slug}),
            reverse(
                'posts:profile', kwargs={'username': self.author.username}
            ),
            reverse('posts:post_detail', kwargs={'post_id': self.post.id}),
        )
        for reverse_name in reverse_names:
            with self.subTest(reverse_name=reverse_name):
                response = self.guest_client.get(reverse_name)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_urls_uses_correct_template(self):
        """
        Проверка URL-адреса на использование соответствующего шаблона.
        """
        reverse_template_names = {
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
        }
        for reverse_name, template in reverse_template_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.guest_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_urls_redirect_anonymous_on_login(self):
        """
        Проверка переадресации анонимного пользователя на страницу авторизации.
        """
        reverse_names = (
            reverse('posts:post_create'),
            reverse('posts:post_edit', kwargs={'post_id': self.post.id}),
            reverse('posts:add_comment', kwargs={'post_id': self.post.id}),
            reverse('posts:follow_index'),
            reverse(
                'posts:profile_follow',
                kwargs={'username': self.author.username},
            ),
            reverse(
                'posts:profile_unfollow',
                kwargs={'username': self.author.username},
            ),
        )
        for reverse_name in reverse_names:
            with self.subTest(revesre_name=reverse_name):
                response = self.guest_client.get(reverse_name, follow=True)
                self.assertRedirects(
                    response,
                    f'/auth/login/?next={reverse_name}',
                )

    def test_urls_only_authorized_client(self):
        """
        Страница доступна только авторизованному пользователю.
        """
        reverse_names = (
            reverse('posts:post_create'),
            reverse('posts:add_comment', kwargs={'post_id': self.post.id}),
            reverse('posts:follow_index'),
            reverse(
                'posts:profile_follow',
                kwargs={'username': self.author.username},
            ),
            reverse(
                'posts:profile_unfollow',
                kwargs={'username': self.author.username},
            ),
        )
        for reverse_name in reverse_names:
            with self.subTest(revesre_name=reverse_name):
                response = self.user_client.get(reverse_name, follow=True)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_user_cannot_edit_author_post(self):
        """
        Проверка при отправке пользователем POST запроса посты не создаются,
        не редактируются и производится переадресация на страницу поста.
        """
        reverse_name = reverse(
            'posts:post_edit', kwargs={'post_id': self.post.id}
        )
        excepted_value = reverse(
            'posts:post_detail', kwargs={'post_id': self.post.id}
        )
        self.new_group = Group.objects.create(
            title='Новая тестовая группа',
            slug='new_test_slug',
            description='Новое тестовое описание группы',
        )
        form_data = {
            'author': self.user,
            'text': 'Измененный тестовый текст',
            'group': self.group.pk,
        }
        response = self.user_client.post(
            reverse_name,
            data=form_data,
            follow=True,
        )
        unmodified_post = Post.objects.get(id=self.post.id)
        self.assertEqual(unmodified_post.author, self.post.author)
        self.assertEqual(unmodified_post.text, self.post.text)
        self.assertEqual(unmodified_post.group, self.post.group)
        self.assertRedirects(response, excepted_value)

    def test_urls_only_author(self):
        """
        Страница доступна только автору поста.
        """
        response = self.author_client.get(
            reverse('posts:post_edit', kwargs={'post_id': self.post.id})
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_unexisting_page(self):
        """
        Несуществующая страница возвращает ошибку 404.
        """
        response = self.guest_client.get('/unexisting_page/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
