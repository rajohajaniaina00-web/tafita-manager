from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from contributions.models import Contribution, Payment
from members.models import Member
from .models import MemberPaymentSubmission
from .models import Notification
from .notification_services import notify_active_members


class CommunityPaymentSecurityTests(TestCase):
    def setUp(self):
        User = get_user_model()

        self.member_user = User.objects.create_user(
            username="community_member_test",
            password="Test-pass-123!",
        )
        self.member = Member.objects.create(
            user=self.member_user,
            first_name="Membre",
            last_name="Test",
            status="active",
        )

        self.other_user = User.objects.create_user(
            username="community_other_test",
            password="Test-pass-123!",
        )
        self.other_member = Member.objects.create(
            user=self.other_user,
            first_name="Autre",
            last_name="Membre",
            status="active",
        )

        self.contribution = Contribution.objects.create(
            member=self.member,
            title="Cotisation annuelle test",
            amount=100000,
        )

        self.other_contribution = Contribution.objects.create(
            member=self.other_member,
            title="Autre cotisation test",
            amount=80000,
        )

    def submission_data(self, amount):
        return {
            "amount": str(amount),
            "method": "mobile_money",
            "reference": "TEST-001",
            "notes": "Test automatisé",
        }

    def test_member_submission_stays_pending_until_approved(self):
        self.client.force_login(self.member_user)

        response = self.client.post(
            reverse(
                "community_submit_payment",
                args=[self.contribution.pk],
            ),
            self.submission_data(25000),
        )

        self.assertEqual(response.status_code, 302)
        submission = MemberPaymentSubmission.objects.get(
            contribution=self.contribution
        )
        self.assertEqual(submission.status, "pending")
        self.assertEqual(submission.amount, 25000)
        self.assertEqual(submission.submitted_by, self.member_user)
        self.assertEqual(
            Payment.objects.filter(
                contribution=self.contribution,
                is_voided=False,
            ).count(),
            0,
        )

    def test_member_cannot_submit_payment_for_another_member(self):
        self.client.force_login(self.other_user)

        response = self.client.post(
            reverse(
                "community_submit_payment",
                args=[self.contribution.pk],
            ),
            self.submission_data(10000),
        )

        self.assertEqual(response.status_code, 404)
        self.assertFalse(
            MemberPaymentSubmission.objects.filter(
                contribution=self.contribution
            ).exists()
        )

    def test_pending_submissions_cannot_exceed_remaining_balance(self):
        self.client.force_login(self.member_user)
        url = reverse(
            "community_submit_payment",
            args=[self.contribution.pk],
        )

        first_response = self.client.post(url, self.submission_data(60000))
        self.assertEqual(first_response.status_code, 302)

        second_response = self.client.post(url, self.submission_data(50000))
        self.assertEqual(second_response.status_code, 302)

        self.assertEqual(
            MemberPaymentSubmission.objects.filter(
                contribution=self.contribution,
                status="pending",
            ).count(),
            1,
        )
        self.assertEqual(Payment.objects.count(), 0)

    def test_regular_member_cannot_approve_payment(self):
        submission = MemberPaymentSubmission.objects.create(
            contribution=self.contribution,
            submitted_by=self.member_user,
            amount=20000,
            method="mobile_money",
            status="pending",
        )
        self.client.force_login(self.member_user)

        response = self.client.post(
            reverse(
                "community_review_payment",
                args=[submission.pk, "approve"],
            )
        )

        self.assertEqual(response.status_code, 403)
        submission.refresh_from_db()
        self.assertEqual(submission.status, "pending")
        self.assertEqual(Payment.objects.count(), 0)

    def test_admin_approval_creates_only_one_payment(self):
        submission = MemberPaymentSubmission.objects.create(
            contribution=self.contribution,
            submitted_by=self.member_user,
            amount=30000,
            method="mobile_money",
            reference="VALIDATION-001",
            status="pending",
        )
        admin_user = get_user_model().objects.create_user(
            username="community_admin_test",
            password="Test-pass-123!",
            is_staff=True,
        )
        self.client.force_login(admin_user)

        url = reverse(
            "community_review_payment",
            args=[submission.pk, "approve"],
        )

        first_response = self.client.post(url)
        self.assertEqual(first_response.status_code, 302)

        submission.refresh_from_db()
        self.assertEqual(submission.status, "approved")

        payments = Payment.objects.filter(
            contribution=self.contribution,
            is_voided=False,
        )
        self.assertEqual(payments.count(), 1)
        self.assertEqual(payments.get().amount, 30000)

        second_response = self.client.post(url)
        self.assertEqual(second_response.status_code, 404)
        self.assertEqual(payments.count(), 1)

class CommunityProfileFallbackTests(TestCase):
    def test_admin_without_member_profile_can_open_account_page(self):
        User = get_user_model()
        admin_user = User.objects.create_user(
            username="admin_profile_without_member",
            password="Test-pass-123!",
            is_staff=True,
        )
        self.client.force_login(admin_user)

        response = self.client.get(reverse("community_member_profile"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "community/profile_admin.html")
        self.assertContains(response, "Votre compte TaFiTa")
        self.assertContains(response, "admin_profile_without_member")

    def test_regular_user_without_member_profile_stays_blocked(self):
        User = get_user_model()
        user = User.objects.create_user(
            username="regular_profile_without_member",
            password="Test-pass-123!",
        )
        self.client.force_login(user)

        response = self.client.get(reverse("community_member_profile"))

        self.assertEqual(response.status_code, 403)
        self.assertTemplateUsed(response, "community/profile_not_linked.html")

class CommunityNotificationTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="notification_member",
            password="Test-pass-123!",
        )
        Member.objects.create(
            user=self.user,
            first_name="Notification",
            last_name="Membre",
            status="active",
        )
        self.other_user = User.objects.create_user(
            username="notification_other_member",
            password="Test-pass-123!",
        )
        Member.objects.create(
            user=self.other_user,
            first_name="Autre",
            last_name="Membre",
            status="active",
        )
        self.own_notification = Notification.objects.create(
            recipient=self.user,
            title="Ma notification",
            message="Message réservé à mon compte.",
            category="system",
        )
        self.other_notification = Notification.objects.create(
            recipient=self.other_user,
            title="Notification privée",
            message="Ce message appartient à un autre compte.",
            category="payment",
        )
        self.client.force_login(self.user)

    def test_user_sees_only_own_notifications(self):
        response = self.client.get(reverse("community_notifications"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ma notification")
        self.assertNotContains(response, "Notification privée")
        self.assertEqual(response.context["unread_count"], 1)

    def test_notification_shows_internal_destination_link(self):
        destination = reverse("community_my_contributions")
        self.own_notification.url = destination
        self.own_notification.save(update_fields=["url"])

        response = self.client.get(reverse("community_notifications"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'href="{destination}"')
        self.assertContains(response, "Ouvrir la page concernée")

    def test_user_can_mark_own_notification_read(self):
        response = self.client.post(
            reverse(
                "community_notification_mark_read",
                args=[self.own_notification.pk],
            )
        )

        self.assertEqual(response.status_code, 302)
        self.own_notification.refresh_from_db()
        self.assertIsNotNone(self.own_notification.read_at)

    def test_user_cannot_mark_another_users_notification_read(self):
        response = self.client.post(
            reverse(
                "community_notification_mark_read",
                args=[self.other_notification.pk],
            )
        )

        self.assertEqual(response.status_code, 404)
        self.other_notification.refresh_from_db()
        self.assertIsNone(self.other_notification.read_at)

    def test_mark_all_read_changes_only_current_users_notifications(self):
        response = self.client.post(
            reverse("community_notifications_mark_all_read")
        )

        self.assertEqual(response.status_code, 302)
        self.own_notification.refresh_from_db()
        self.other_notification.refresh_from_db()
        self.assertIsNotNone(self.own_notification.read_at)
        self.assertIsNone(self.other_notification.read_at)


class CommunityPaymentNotificationTests(TestCase):
    def test_rejection_notifies_the_submitter(self):
        User = get_user_model()
        member_user = User.objects.create_user(
            username="payment_rejection_member",
            password="Test-pass-123!",
        )
        member = Member.objects.create(
            user=member_user,
            first_name="Membre",
            last_name="Notification",
            status="active",
        )
        contribution = Contribution.objects.create(
            member=member,
            title="Cotisation notification",
            amount=60000,
        )
        submission = MemberPaymentSubmission.objects.create(
            contribution=contribution,
            submitted_by=member_user,
            amount=10000,
            method="mobile_money",
            status="pending",
        )
        admin_user = User.objects.create_user(
            username="payment_rejection_admin",
            password="Test-pass-123!",
            is_staff=True,
        )
        self.client.force_login(admin_user)

        response = self.client.post(
            reverse(
                "community_review_payment",
                args=[submission.pk, "reject"],
            ),
            {"rejection_reason": "Justificatif illisible"},
        )

        self.assertEqual(response.status_code, 302)
        notification = Notification.objects.get(
            recipient=member_user,
            category="payment",
            title="Déclaration de paiement refusée",
        )
        self.assertIn("Justificatif illisible", notification.message)
        self.assertEqual(
            notification.url,
            reverse("community_my_contributions"),
        )


class ActiveMemberNotificationServiceTests(TestCase):
    def test_only_active_members_with_accounts_are_notified(self):
        User = get_user_model()

        active_user = User.objects.create_user(
            username="active_notification_member",
            password="Test-pass-123!",
        )
        Member.objects.create(
            user=active_user,
            first_name="Actif",
            last_name="Notification",
            status="active",
        )

        inactive_user = User.objects.create_user(
            username="inactive_notification_member",
            password="Test-pass-123!",
        )
        Member.objects.create(
            user=inactive_user,
            first_name="Inactif",
            last_name="Notification",
            status="inactive",
        )

        created = notify_active_members(
            title="Nouvel événement : Test",
            message="Notification de test.",
            category="event",
            url="/communaute/",
        )

        self.assertEqual(len(created), 1)
        self.assertEqual(created[0].recipient_id, active_user.pk)
        self.assertFalse(
            Notification.objects.filter(recipient=inactive_user).exists()
        )
