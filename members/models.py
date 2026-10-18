from django.db import models
from django.utils import timezone


class Member(models.Model):
    STATUS_CHOICES = [
        ("active", "Actif"),
        ("inactive", "Inactif"),
    ]

    first_name = models.CharField("Prénom", max_length=100)
    last_name = models.CharField("Nom", max_length=100)
    email = models.EmailField("Adresse e-mail", blank=True, null=True, unique=True)
    phone = models.CharField("Téléphone", max_length=30, blank=True)
    joined_on = models.DateField(
        "Date d'adhésion",
        default=timezone.localdate,
    )
    status = models.CharField(
        "Statut",
        max_length=10,
        choices=STATUS_CHOICES,
        default="active",
    )
    notes = models.TextField("Notes", blank=True)
    created_at = models.DateTimeField("Créé le", auto_now_add=True)
    updated_at = models.DateTimeField("Modifié le", auto_now=True)

    class Meta:
        ordering = ["last_name", "first_name"]
        verbose_name = "Membre"
        verbose_name_plural = "Membres"

    def __str__(self):
        return f"{self.first_name} {self.last_name}"