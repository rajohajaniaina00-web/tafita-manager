
from django.db import models


class Event(models.Model):
    STATUS_CHOICES = [
        ("planned", "Planifié"),
        ("ongoing", "En cours"),
        ("completed", "Terminé"),
        ("cancelled", "Annulé"),
    ]

    title = models.CharField(
        max_length=200,
        verbose_name="Titre"
    )

    description = models.TextField(
        blank=True,
        verbose_name="Description"
    )

    date = models.DateTimeField(
        verbose_name="Date et heure de début"
    )

    end_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Date et heure de fin"
    )

    location = models.CharField(
        max_length=200,
        verbose_name="Lieu"
    )

    responsible = models.CharField(
        max_length=150,
        verbose_name="Responsable"
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="planned",
        verbose_name="Statut"
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Date de création"
    )

    class Meta:
        ordering = ["date"]
        verbose_name = "Événement"
        verbose_name_plural = "Événements"

    @property
    def current_status(self):
        from django.utils import timezone

        if self.status == "cancelled":
            return "cancelled"

        now = timezone.now()

        if now < self.date:
            return "planned"

        if self.end_date is not None:
            if now < self.end_date:
                return "ongoing"
            return "completed"

        # Pour les anciens événements sans date de fin :
        # actif le jour de l'événement, terminé les jours suivants.
        event_day = (
            timezone.localtime(self.date).date()
            if timezone.is_aware(self.date)
            else self.date.date()
        )
        if timezone.localdate() == event_day:
            return "ongoing"

        return "completed"

    @property
    def current_status_display(self):
        return dict(self.STATUS_CHOICES).get(
            self.current_status,
            "Inconnu"
        )
    def __str__(self):
        return self.title
