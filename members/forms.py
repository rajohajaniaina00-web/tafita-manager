
from django import forms
from .models import Member


class MemberForm(forms.ModelForm):
    class Meta:
        model = Member

        fields = [
            "user",
            "first_name",
            "last_name",
            "email",
            "phone",
            "joined_on",
            "status",
            "notes",
        ]

        labels = {
            "user": "Compte utilisateur associé",
        }

        widgets = {
            "joined_on": forms.DateInput(
                attrs={"type": "date"}
            ),
            "notes": forms.Textarea(
                attrs={"rows": 4}
            ),
        }
