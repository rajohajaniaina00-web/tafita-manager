from events.models import Event
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from members.models import Member
from contributions.models import Contribution, Payment


class DashboardPaymentAuditTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="dashboard_audit_test",
            password="Test-pass-123!",
        )

        permission = Permission.objects.get(
            content_type__app_label="contributions",
            codename="view_contribution",
        )
        self.user.user_permissions.add(permission)

        self.member = Member.objects.create(
            user=self.user,
            first_name="Test",
            last_name="Dashboard",
        )

        self.contribution = Contribution.objects.create(
            member=self.member,
            title="Cotisation de contrôle",
            amount=50000,
            due_date=timezone.localdate() - timedelta(days=1),
        )

        self.valid_payment = Payment.objects.create(
            contribution=self.contribution,
            amount=10000,
            payment_date=timezone.localdate(),
            method="cash",
        )

        self.voided_payment = Payment.objects.create(
            contribution=self.contribution,
            amount=5000,
            payment_date=timezone.localdate(),
            method="cash",
            is_voided=True,
            voided_at=timezone.now(),
            void_reason="Test d'annulation",
        )

        self.client.force_login(self.user)

    def test_admin_dashboard_excludes_voided_payments(self):
        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["paid_total"], 10000)
        self.assertEqual(response.context["remaining_total"], 40000)
        self.assertEqual(response.context["overdue_total"], 40000)

        recent_payments = list(response.context["recent_payments"])
        self.assertEqual(
            [payment.pk for payment in recent_payments],
            [self.valid_payment.pk],
        )

        self.assertEqual(sum(response.context["month_values"]), 10000)

    def test_member_dashboard_excludes_voided_payments(self):
        response = self.client.get(reverse("member_home"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_paid"], 10000)
        self.assertEqual(response.context["remaining_total"], 40000)

        latest_payments = list(response.context["latest_payments"])
        self.assertEqual(
            [payment.pk for payment in latest_payments],
            [self.valid_payment.pk],
        )

    def test_dashboard_denies_user_without_relevant_permission(self):
        User = get_user_model()
        user = User.objects.create_user(
            username="dashboard_no_permission",
            password="Test-pass-123!",
        )
        self.client.force_login(user)

        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 403)

    def test_dashboard_counts_ongoing_events_as_active(self):
        permission = Permission.objects.get(
            content_type__app_label="events",
            codename="view_event",
        )
        self.user.user_permissions.add(permission)

        now = timezone.now()
        event = Event.objects.create(
            title="Activité en cours",
            date=now - timedelta(hours=1),
            end_date=now + timedelta(hours=1),
            location="Antananarivo",
            responsible="Responsable test",
            status="planned",
        )

        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["events_upcoming_count"], 1)
        self.assertIn(event, list(response.context["next_events"]))
