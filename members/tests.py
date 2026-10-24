from django.test import TestCase
from .models import Member


class MemberModelTests(TestCase):
    def test_new_member_is_active_by_default(self):
        member = Member.objects.create(
            first_name="Test",
            last_name="Membre",
        )
        self.assertEqual(member.status, "active")

    def test_member_can_be_created_without_user_account(self):
        member = Member.objects.create(
            first_name="Sans",
            last_name="Compte",
        )
        self.assertIsNone(member.user_id)

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.urls import reverse


class MemberAccessTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="test_member_access",
            password="Test-pass-123!",
        )
        self.url = reverse("member_list")

    def test_anonymous_user_is_redirected_to_login(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response["Location"].startswith("/accounts/login/"))

    def test_logged_in_user_without_permission_gets_forbidden(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)

    def test_user_with_view_permission_can_open_member_list(self):
        permission = Permission.objects.get(
            content_type__app_label="members",
            codename="view_member",
        )
        self.user.user_permissions.add(permission)
        self.client.force_login(self.user)

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
