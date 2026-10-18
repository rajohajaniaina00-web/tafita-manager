
from django.db import models
from django.db.models import Sum
from django.utils import timezone


class Contribution(models.Model):
    member = models.ForeignKey(
        "members.Member",
        on_delete=models.PROTECT,
        related_name="contributions",
        verbose_name="Membre",
    )
    title = models.CharField(
        "Libellé",
        max_length=150,
    )
    amount = models.PositiveBigIntegerField(
        "Montant attendu (Ar)",
    )
    due_date = models.DateField(
        "Date limite",
        null=True,
        blank=True,
    )
    description = models.TextField(
        "Description",
        blank=True,
    )
    created_at = models.DateTimeField(
        "Créée le",
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Cotisation"
        verbose_name_plural = "Cotisations"

    def __str__(self):
        return f"{self.title} — {self.member}"

    @property
    def total_paid(self):
        result = self.payments.aggregate(
            total=Sum("amount")
        )["total"]
        return result or 0

    @property
    def remaining_amount(self):
        return max(self.amount - self.total_paid, 0)

    @property
    def current_status(self):
        if self.total_paid >= self.amount:
            return "paid"
        if self.total_paid > 0:
            return "partial"
        return "unpaid"

    @property
    def current_status_display(self):
        labels = {
            "paid": "Payée",
            "partial": "Partielle",
            "unpaid": "Impayée",
        }
        return labels[self.current_status]


class Payment(models.Model):
    contribution = models.ForeignKey(
        Contribution,
        on_delete=models.PROTECT,
        related_name="payments",
        verbose_name="Cotisation",
    )
    amount = models.PositiveBigIntegerField(
        "Montant versé (Ar)",
    )
    payment_date = models.DateField(
        "Date du paiement",
        default=timezone.localdate,
    )
    method = models.CharField(
        "Mode de paiement",
        max_length=30,
        choices=[
            ("cash", "Espèces"),
            ("mobile_money", "Mobile Money"),
            ("bank", "Virement bancaire"),
            ("other", "Autre"),
        ],
        default="cash",
    )
    reference = models.CharField(
        "Référence",
        max_length=100,
        blank=True,
    )
    notes = models.TextField(
        "Notes",
        blank=True,
    )
    created_at = models.DateTimeField(
        "Enregistré le",
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-payment_date", "-created_at"]
        verbose_name = "Paiement"
        verbose_name_plural = "Paiements"

    def __str__(self):
        return (
            f"{self.contribution.title} — "
            f"{self.amount} Ar — {self.payment_date}"
        )
