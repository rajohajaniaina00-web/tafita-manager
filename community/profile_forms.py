from django import forms
from django.core.validators import FileExtensionValidator


class MemberPhotoForm(forms.Form):
    photo = forms.ImageField(
        label="Choisir une photo",
        required=False,
        validators=[FileExtensionValidator(["jpg", "jpeg", "png", "webp"])],
        widget=forms.ClearableFileInput(attrs={
            "accept": "image/jpeg,image/png,image/webp",
            "class": "profile-file-input",
        }),
        help_text="JPG, PNG ou WEBP — 5 Mo maximum.",
    )

    def clean_photo(self):
        photo = self.cleaned_data.get("photo")
        if photo and photo.size > 5 * 1024 * 1024:
            raise forms.ValidationError("La photo ne doit pas dépasser 5 Mo.")
        return photo
