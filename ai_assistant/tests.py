from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from members.models import Member
from contributions.models import Contribution, Payment
from .views import get_association_snapshot


class AssistantFinancialSnapshotTests(TestCase):
    def setUp(self):
        member = Member.objects.create(
            first_name="Test",
            last_name="Finances",
        )

        contribution = Contribution.objects.create(
            member=member,
            title="Cotisation de test",
            amount=50000,
            due_date=timezone.localdate() - timedelta(days=1),
        )

        Payment.objects.create(
            contribution=contribution,
            amount=10000,
            method="cash",
        )

        Payment.objects.create(
            contribution=contribution,
            amount=5000,
            method="cash",
            is_voided=True,
            voided_at=timezone.now(),
            void_reason="Test d'annulation",
        )

    def test_snapshot_excludes_voided_payments(self):
        snapshot = get_association_snapshot()
        contributions = snapshot["contributions"]

        self.assertEqual(
            contributions["payments_recorded_ariary"], 10000
        )
        self.assertEqual(contributions["remaining_ariary"], 40000)
        self.assertEqual(
            contributions["overdue_contributions_count"], 1
        )
        self.assertEqual(contributions["overdue_amount_ariary"], 40000)
