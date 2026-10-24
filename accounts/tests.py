from django.test import TestCase

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.urls import reverse


class AdminLoginTests(TestCase):
    def test_admin_with_permission_can_log_in(self):
        User = get_user_model()
        user = User.objects.create_user(
            username="test_admin_login",
            password="Test-pass-123!",
        )
        permission = Permission.objects.get(
            content_type__app_label="members",
            codename="view_member",
        )
        user.user_permissions.add(permission)

        response = self.client.post(
            reverse("login"),
            {"username": "test_admin_login", "password": "Test-pass-123!"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("dashboard"))

    def test_regular_user_is_not_allowed_into_admin_login(self):
        User = get_user_model()
        User.objects.create_user(
            username="test_regular_login",
            password="Test-pass-123!",
        )

        response = self.client.post(
            reverse("login"),
            {"username": "test_regular_login", "password": "Test-pass-123!"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)
