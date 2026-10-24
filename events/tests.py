from community.models import Notification
from members.models import Member
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.utils import timezone
from django.urls import reverse

from .models import Event


class EventStatusTests(TestCase):
    def create_event(self, start, end, status="planned"):
        return Event.objects.create(
            title="Événement de test",
            description="",
            date=start,
            end_date=end,
            location="Antananarivo",
            responsible="Responsable test",
            status=status,
        )

    def test_future_event_is_planned(self):
        now = timezone.now()
        event = self.create_event(
            now + timedelta(days=2),
            now + timedelta(days=3),
        )
        self.assertEqual(event.current_status, "planned")

    def test_event_in_progress_is_ongoing(self):
        now = timezone.now()
        event = self.create_event(
            now - timedelta(hours=1),
            now + timedelta(hours=1),
        )
        self.assertEqual(event.current_status, "ongoing")

    def test_past_event_is_completed(self):
        now = timezone.now()
        event = self.create_event(
            now - timedelta(days=3),
            now - timedelta(days=2),
        )
        self.assertEqual(event.current_status, "completed")

    def test_cancelled_event_stays_cancelled(self):
        now = timezone.now()
        event = self.create_event(
            now + timedelta(days=2),
            now + timedelta(days=3),
            status="cancelled",
        )
        self.assertEqual(event.current_status, "cancelled")

    def test_event_without_end_date_is_ongoing_on_its_day(self):
        now = timezone.now()
        event = self.create_event(
            now - timedelta(hours=1),
            None,
        )
        self.assertEqual(event.current_status, "ongoing")

    def test_old_event_without_end_date_is_completed(self):
        now = timezone.now()
        event = self.create_event(
            now - timedelta(days=2),
            None,
        )
        self.assertEqual(event.current_status, "completed")


class EventAccessTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="test_event_access",
            password="Test-pass-123!",
        )
        self.url = reverse("events_list")

    def test_anonymous_user_is_redirected_to_login(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            response["Location"].startswith("/accounts/login/")
        )

    def test_logged_in_user_without_permission_gets_forbidden(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)

    def test_user_with_view_permission_can_open_event_list(self):
        permission = Permission.objects.get(
            content_type__app_label="events",
            codename="view_event",
        )
        self.user.user_permissions.add(permission)
        self.client.force_login(self.user)

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)


class EventNotificationTests(TestCase):
    def test_new_event_notifies_active_members_with_accounts(self):
        User = get_user_model()

        member_user = User.objects.create_user(
            username="event_notification_member",
            password="Test-pass-123!",
        )
        Member.objects.create(
            user=member_user,
            first_name="Membre",
            last_name="Événement",
            status="active",
        )

        admin_user = User.objects.create_user(
            username="event_notification_admin",
            password="Test-pass-123!",
        )
        permission = Permission.objects.get(
            content_type__app_label="events",
            codename="add_event",
        )
        admin_user.user_permissions.add(permission)
        self.client.force_login(admin_user)

        start = timezone.localtime(
            timezone.now() + timedelta(days=2)
        ).strftime("%Y-%m-%dT%H:%M")
        end = timezone.localtime(
            timezone.now() + timedelta(days=2, hours=2)
        ).strftime("%Y-%m-%dT%H:%M")

        response = self.client.post(
            reverse("event_create"),
            {
                "title": "Activité de notification",
                "description": "Test de création",
                "date": start,
                "end_date": end,
                "location": "Antananarivo",
                "responsible": "Responsable test",
            },
        )

        self.assertEqual(response.status_code, 302)
        notification = Notification.objects.get(
            recipient=member_user,
            category="event",
            title="Nouvel événement : Activité de notification",
        )
        self.assertIn("Antananarivo", notification.message)
        self.assertTrue(notification.url.startswith("/communaute/evenement/"))


class EventLifecycleNotificationTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.member_user = User.objects.create_user(
            username="event_lifecycle_member",
            password="Test-pass-123!",
        )
        Member.objects.create(
            user=self.member_user,
            first_name="Membre",
            last_name="Événement",
            status="active",
        )

        self.admin = User.objects.create_user(
            username="event_lifecycle_admin",
            password="Test-pass-123!",
        )
        permission = Permission.objects.get(
            content_type__app_label="events",
            codename="change_event",
        )
        self.admin.user_permissions.add(permission)
        self.client.force_login(self.admin)

        now = timezone.now()
        self.event = Event.objects.create(
            title="Réunion initiale",
            description="Description initiale",
            date=now + timedelta(days=3),
            end_date=now + timedelta(days=3, hours=2),
            location="Antananarivo",
            responsible="Responsable test",
            status="planned",
        )

    def event_form_data(self, **overrides):
        start = timezone.localtime(
            self.event.date
        ).strftime("%Y-%m-%dT%H:%M")
        end = timezone.localtime(
            self.event.end_date
        ).strftime("%Y-%m-%dT%H:%M")

        data = {
            "title": self.event.title,
            "description": self.event.description,
            "date": start,
            "end_date": end,
            "location": self.event.location,
            "responsible": self.event.responsible,
        }
        data.update(overrides)
        return data

    def test_modified_event_notifies_active_members(self):
        response = self.client.post(
            reverse("event_update", args=[self.event.pk]),
            self.event_form_data(title="Réunion mise à jour"),
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.member_user,
                category="event",
                title="Événement modifié : Réunion mise à jour",
            ).exists()
        )

    def test_cancelled_event_notifies_active_members(self):
        response = self.client.post(
            reverse("event_update", args=[self.event.pk]),
            self.event_form_data(cancelled="on"),
        )

        self.assertEqual(response.status_code, 302)
        self.event.refresh_from_db()
        self.assertEqual(self.event.status, "cancelled")
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.member_user,
                category="event",
                title="Événement annulé : Réunion initiale",
            ).exists()
        )
