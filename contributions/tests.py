from django.test import TestCase
from django.utils import timezone

from members.models import Member
from .forms import ContributionForm, PaymentForm
from .models import Contribution, Payment


class ContributionStatusTests(TestCase):
    def setUp(self):
        self.member = Member.objects.create(
            first_name="Test",
            last_name="Membre",
        )
        self.contribution = Contribution.objects.create(
            member=self.member,
            title="Cotisation annuelle",
            amount=100000,
        )

    def add_payment(self, amount):
        return Payment.objects.create(
            contribution=self.contribution,
            amount=amount,
            payment_date=timezone.localdate(),
            method="cash",
        )

    def test_contribution_starts_unpaid(self):
        self.assertEqual(self.contribution.total_paid, 0)
        self.assertEqual(self.contribution.remaining_amount, 100000)
        self.assertEqual(self.contribution.current_status, "unpaid")

    def test_partial_payment_updates_balance(self):
        self.add_payment(30000)
        self.contribution.refresh_from_db()

        self.assertEqual(self.contribution.total_paid, 30000)
        self.assertEqual(self.contribution.remaining_amount, 70000)
        self.assertEqual(self.contribution.current_status, "partial")

    def test_full_payment_marks_contribution_paid(self):
        self.add_payment(100000)
        self.contribution.refresh_from_db()

        self.assertEqual(self.contribution.remaining_amount, 0)
        self.assertEqual(self.contribution.current_status, "paid")

    def test_payment_form_accepts_valid_partial_payment(self):
        form = PaymentForm(
            data={
                "amount": "35000",
                "payment_date": timezone.localdate().isoformat(),
                "method": "cash",
                "reference": "",
                "notes": "",
            },
            contribution=self.contribution,
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_payment_form_rejects_amount_above_remaining_balance(self):
        form = PaymentForm(
            data={
                "amount": "100001",
                "payment_date": timezone.localdate().isoformat(),
                "method": "cash",
                "reference": "",
                "notes": "",
            },
            contribution=self.contribution,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("amount", form.errors)

    def test_payment_form_rejects_zero_amount(self):
        form = PaymentForm(
            data={
                "amount": "0",
                "payment_date": timezone.localdate().isoformat(),
                "method": "cash",
                "reference": "",
                "notes": "",
            },
            contribution=self.contribution,
        )
        self.assertFalse(form.is_valid())

    def test_contribution_form_rejects_zero_expected_amount(self):
        form = ContributionForm(
            data={
                "member": str(self.member.pk),
                "title": "Montant invalide",
                "amount": "0",
                "due_date": "",
                "description": "",
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("amount", form.errors)

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.urls import reverse


class ContributionAccessTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="test_contribution_access",
            password="Test-pass-123!",
        )
        self.member = Member.objects.create(
            first_name="Test",
            last_name="Cotisation",
        )
        self.contribution = Contribution.objects.create(
            member=self.member,
            title="Cotisation de contrôle",
            amount=50000,
        )

    def test_anonymous_user_is_redirected_from_payment_page(self):
        response = self.client.get(
            reverse("payment_create", args=[self.contribution.pk])
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response["Location"].startswith("/accounts/login/"))

    def test_user_without_add_payment_permission_gets_forbidden(self):
        self.client.force_login(self.user)
        response = self.client.get(
            reverse("payment_create", args=[self.contribution.pk])
        )
        self.assertEqual(response.status_code, 403)

    def test_user_with_add_payment_permission_can_open_payment_form(self):
        permission = Permission.objects.get(
            content_type__app_label="contributions",
            codename="add_payment",
        )
        self.user.user_permissions.add(permission)
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("payment_create", args=[self.contribution.pk])
        )
        self.assertEqual(response.status_code, 200)

    def test_user_without_view_permission_cannot_open_contribution_list(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("contribution_list"))
        self.assertEqual(response.status_code, 403)

class PaymentEndpointSecurityTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="test_payment_security",
            password="Test-pass-123!",
        )
        self.member = Member.objects.create(
            first_name="Test",
            last_name="Paiement",
        )
        self.contribution = Contribution.objects.create(
            member=self.member,
            title="Cotisation sécurité",
            amount=50000,
        )
        self.payment_url = reverse(
            "payment_create",
            args=[self.contribution.pk],
        )

    def grant_permission(self, codename):
        permission = Permission.objects.get(
            content_type__app_label="contributions",
            codename=codename,
        )
        self.user.user_permissions.add(permission)

    def payment_data(self, amount):
        return {
            "amount": str(amount),
            "payment_date": timezone.localdate().isoformat(),
            "method": "cash",
            "reference": "",
            "notes": "",
        }

    def test_overpayment_is_rejected_by_payment_view(self):
        self.grant_permission("add_payment")
        self.client.force_login(self.user)

        response = self.client.post(
            self.payment_url,
            self.payment_data(50001),
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Payment.objects.count(), 0)
        self.contribution.refresh_from_db()
        self.assertEqual(self.contribution.remaining_amount, 50000)

    def test_authorized_partial_payment_updates_balance(self):
        self.grant_permission("add_payment")
        self.client.force_login(self.user)

        response = self.client.post(
            self.payment_url,
            self.payment_data(20000),
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Payment.objects.count(), 1)
        self.contribution.refresh_from_db()
        self.assertEqual(self.contribution.remaining_amount, 30000)

    def test_user_without_delete_permission_cannot_delete_payment(self):
        payment = Payment.objects.create(
            contribution=self.contribution,
            amount=10000,
            method="cash",
        )
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("payment_delete", args=[payment.pk])
        )

        self.assertEqual(response.status_code, 403)
        self.assertTrue(Payment.objects.filter(pk=payment.pk).exists())

    def test_payment_deletion_requires_post(self):
        payment = Payment.objects.create(
            contribution=self.contribution,
            amount=10000,
            method="cash",
        )
        self.grant_permission("delete_payment")
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("payment_delete", args=[payment.pk])
        )

        self.assertEqual(response.status_code, 405)
        self.assertTrue(Payment.objects.filter(pk=payment.pk).exists())


    def test_payment_cancellation_requires_reason(self):
        payment = Payment.objects.create(
            contribution=self.contribution,
            amount=10000,
            method="cash",
        )
        self.grant_permission("delete_payment")
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("payment_delete", args=[payment.pk]),
            {"reason": "   "},
        )

        self.assertEqual(response.status_code, 302)
        payment.refresh_from_db()
        self.assertFalse(payment.is_voided)
        self.assertEqual(payment.void_reason, "")

    def test_authorized_payment_deletion_restores_remaining_balance(self):
        payment = Payment.objects.create(
            contribution=self.contribution,
            amount=10000,
            method="cash",
        )
        self.grant_permission("delete_payment")
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("payment_delete", args=[payment.pk]),
            {"reason": "Erreur de saisie"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(Payment.objects.filter(pk=payment.pk).exists())
        payment.refresh_from_db()
        self.assertTrue(payment.is_voided)
        self.assertEqual(payment.voided_by, self.user)
        self.contribution.refresh_from_db()
        self.assertEqual(self.contribution.remaining_amount, 50000)

    def test_voided_payment_is_excluded_from_balance(self):
        payment = Payment.objects.create(
            contribution=self.contribution,
            amount=10000,
            method="cash",
        )
        payment.is_voided = True
        payment.save(update_fields=["is_voided"])

        self.contribution.refresh_from_db()
        self.assertEqual(self.contribution.total_paid, 0)
        self.assertEqual(self.contribution.remaining_amount, 50000)
        self.assertEqual(self.contribution.current_status, "unpaid")
