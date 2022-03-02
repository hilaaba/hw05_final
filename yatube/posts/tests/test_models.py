from django.contrib.auth import get_user_model
from django.test import TestCase

from ..models import Group, Post

User = get_user_model()


class PostModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test_slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост c количеством символов больше 15',
        )

    def test_models_have_correct_object_names(self):
        """Проверяем, что у моделей корректно работает __str__."""
        object_names = {
            str(PostModelTest.post): self.post.text[:15],
            str(PostModelTest.group): self.group.title,
        }
        for object_name, excepted_value in object_names.items():
            with self.subTest(object_name=object_name):
                self.assertEqual(object_name, excepted_value)
