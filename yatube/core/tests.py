from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

User = get_user_model()


class CoreViewsTests(TestCase):
    def setUp(self):
        self.guest_client = Client()

    def test_unexisting_page(self):
        """
        Несуществующая страница возвращает ошибку 404.
        """
        response = self.guest_client.get('/unexisting_page/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        self.assertTemplateUsed(response, 'core/404.html')
