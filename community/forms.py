from django import forms

from .models import CommunityPost, PostComment, EventComment, ConversationMessage
from .models import MemberPaymentSubmission


class MemberRegistrationForm(forms.Form):
    activation_code = forms.CharField(
        label="Code d’activation", max_length=80,
        widget=forms.TextInput(attrs={"autocomplete": "one-time-code", "placeholder": "Code fourni par TaFiTa"}),
    )
    username = forms.CharField(
        label="Nom d’utilisateur", max_length=150,
        widget=forms.TextInput(attrs={"autocomplete": "username", "placeholder": "Choisissez un identifiant"}),
    )
    email = forms.EmailField(
        label="Adresse e-mail (facultatif)", required=False,
        widget=forms.EmailInput(attrs={"autocomplete": "email", "placeholder": "vous@exemple.com"}),
    )
    password1 = forms.CharField(
        label="Mot de passe", strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )
    password2 = forms.CharField(
        label="Confirmer le mot de passe", strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )


class MemberLoginForm(forms.Form):
    username = forms.CharField(label="Nom d’utilisateur", max_length=150)
    password = forms.CharField(label="Mot de passe", strip=False, widget=forms.PasswordInput)


class CommunityPostForm(forms.ModelForm):
    class Meta:
        model = CommunityPost
        fields = ["content", "image"]
        widgets = {
            "content": forms.Textarea(attrs={
                "rows": 3,
                "placeholder": "Partagez une nouvelle avec la communauté TaFiTa…",
                "maxlength": 5000,
            }),
            "image": forms.ClearableFileInput(attrs={"accept": "image/jpeg,image/png,image/webp"}),
        }

    def clean(self):
        cleaned = super().clean()
        content = (cleaned.get("content") or "").strip()
        image = cleaned.get("image")
        if not content and not image:
            raise forms.ValidationError("Ajoutez un texte ou une image à votre publication.")
        if image and getattr(image, "size", 0) > 5 * 1024 * 1024:
            self.add_error("image", "L’image ne doit pas dépasser 5 Mo.")
        if image:
            allowed = {"image/jpeg", "image/png", "image/webp"}
            content_type = getattr(image, "content_type", None)
            if content_type and content_type not in allowed:
                self.add_error("image", "Formats acceptés : JPEG, PNG ou WebP.")
        return cleaned


class PostCommentForm(forms.ModelForm):
    class Meta:
        model = PostComment
        fields = ["content"]
        widgets = {"content": forms.TextInput(attrs={"placeholder": "Écrire un commentaire…", "maxlength": 1500})}


class EventCommentForm(forms.ModelForm):
    class Meta:
        model = EventComment
        fields = ["content"]
        widgets = {"content": forms.TextInput(attrs={"placeholder": "Commenter cet événement…", "maxlength": 1500})}


class ConversationMessageForm(forms.ModelForm):
    class Meta:
        model = ConversationMessage
        fields = ["content"]
        widgets = {"content": forms.TextInput(attrs={"placeholder": "Écrire un message…", "maxlength": 4000, "autocomplete": "off"})}


class GroupConversationForm(forms.Form):
    title = forms.CharField(label="Nom du groupe", max_length=140)
    participants = forms.ModelMultipleChoiceField(
        label="Ajouter des membres",
        queryset=None,
        required=False,
        widget=forms.SelectMultiple(attrs={"size": 6}),
    )

    def __init__(self, *args, eligible_users=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["participants"].queryset = eligible_users if eligible_users is not None else self.fields["participants"].queryset.none()


class MemberPaymentSubmissionForm(forms.ModelForm):
    class Meta:
        model = MemberPaymentSubmission
        fields = ["amount", "method", "reference", "proof", "notes"]
        widgets = {
            "amount": forms.NumberInput(attrs={"min": 1, "step": 1, "placeholder": "Montant en Ariary"}),
            "method": forms.Select(),
            "reference": forms.TextInput(attrs={"maxlength": 100, "placeholder": "Référence de transaction (si disponible)"}),
            "proof": forms.ClearableFileInput(attrs={"accept": ".jpg,.jpeg,.png,.webp,.pdf"}),
            "notes": forms.Textarea(attrs={"rows": 3, "maxlength": 500, "placeholder": "Information complémentaire (facultatif)"}),
        }

    def clean_proof(self):
        proof = self.cleaned_data.get("proof")
        if proof and proof.size > 8 * 1024 * 1024:
            raise forms.ValidationError("Le justificatif ne doit pas dépasser 8 Mo.")
        return proof

    def clean_amount(self):
        amount = self.cleaned_data.get("amount")
        if amount is None or amount <= 0:
            raise forms.ValidationError("Le montant doit être supérieur à zéro.")
        return amount
