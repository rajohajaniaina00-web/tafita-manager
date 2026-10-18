from django import forms
from django.core.exceptions import ValidationError

from .models import Contribution, Payment


class ContributionForm(forms.ModelForm):
    class Meta:
        model = Contribution
        fields = [
            "member",
            "title",
            "amount",
            "due_date",
            "description",
        ]
        widgets = {
            "due_date": forms.DateInput(
                attrs={"type": "date"}
            ),
            "description": forms.Textarea(
                attrs={"rows": 4}
            ),
        }

    def clean_amount(self):
        amount = self.cleaned_data["amount"]

        if amount <= 0:
            raise ValidationError(
                "Le montant attendu doit être supérieur à 0 Ar."
            )

        return amount


class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = [
            "amount",
            "payment_date",
            "method",
            "reference",
            "notes",
        ]
        widgets = {
            "payment_date": forms.DateInput(
                attrs={"type": "date"}
            ),
            "notes": forms.Textarea(
                attrs={"rows": 3}
            ),
        }

    def __init__(self, *args, contribution=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.contribution = contribution

    def clean_amount(self):
        amount = self.cleaned_data["amount"]

        if amount <= 0:
            raise ValidationError(
                "Le montant versé doit être supérieur à 0 Ar."
            )

        if self.contribution:
            remaining = self.contribution.remaining_amount

            if amount > remaining:
                raise ValidationError(
                    f"Le montant dépasse le reste à payer "
                    f"({remaining:,} Ar).".replace(",", " ")
                )

        return amount
