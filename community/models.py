from django.conf import settings
from django.db import models
from django.db.models import Q
from django.core.validators import FileExtensionValidator
from django.utils import timezone


class MemberInvitation(models.Model):
    """Single-use, expiring invitation to activate one Member account."""
    member = models.OneToOneField(
        "members.Member",
        on_delete=models.CASCADE,
        related_name="community_invitation",
        verbose_name="Membre",
    )
    code = models.CharField("Code d’activation", max_length=80, unique=True)
    created_at = models.DateTimeField("Créé le", auto_now_add=True)
    expires_at = models.DateTimeField("Expire le")
    used_at = models.DateTimeField("Utilisé le", null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_member_invitations",
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Invitation de membre"
        verbose_name_plural = "Invitations de membres"

    @property
    def is_valid(self):
        return (
            self.used_at is None
            and self.expires_at > timezone.now()
            and self.member.user_id is None
            and self.member.status == "active"
        )

    def __str__(self):
        return f"Invitation — {self.member}"


class CommunityPost(models.Model):
    STATUS_CHOICES = [
        ("pending", "En attente"),
        ("approved", "Publiée"),
        ("rejected", "Refusée"),
    ]
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="community_posts",
    )
    content = models.TextField("Texte", blank=True, max_length=5000)
    image = models.ImageField(
        "Image", upload_to="community/posts/%Y/%m/", blank=True, null=True
    )
    status = models.CharField(
        "Statut", max_length=12, choices=STATUS_CHOICES, default="pending"
    )
    moderation_note = models.CharField("Note de modération", max_length=300, blank=True)
    created_at = models.DateTimeField("Créée le", auto_now_add=True)
    updated_at = models.DateTimeField("Modifiée le", auto_now=True)
    moderated_at = models.DateTimeField("Modérée le", null=True, blank=True)
    moderated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="moderated_community_posts",
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status", "-created_at"])]
        verbose_name = "Publication communautaire"
        verbose_name_plural = "Publications communautaires"

    def __str__(self):
        return f"Publication de {self.author} ({self.get_status_display()})"


class PostComment(models.Model):
    post = models.ForeignKey(CommunityPost, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="community_post_comments"
    )
    content = models.CharField("Commentaire", max_length=1500)
    created_at = models.DateTimeField("Publié le", auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Commentaire de {self.author}"


class PostReaction(models.Model):
    post = models.ForeignKey(CommunityPost, on_delete=models.CASCADE, related_name="reactions")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="community_post_reactions"
    )
    reaction = models.CharField(max_length=12, default="love", editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["post", "user"], name="unique_post_reaction_per_user")]


class EventComment(models.Model):
    event = models.ForeignKey("events.Event", on_delete=models.CASCADE, related_name="community_comments")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="community_event_comments"
    )
    content = models.CharField("Commentaire", max_length=1500)
    created_at = models.DateTimeField("Publié le", auto_now_add=True)

    class Meta:
        ordering = ["created_at"]


class EventReaction(models.Model):
    event = models.ForeignKey("events.Event", on_delete=models.CASCADE, related_name="community_reactions")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="community_event_reactions"
    )
    reaction = models.CharField(max_length=12, default="love", editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["event", "user"], name="unique_event_reaction_per_user")]


class Conversation(models.Model):
    TYPE_CHOICES = [
        ("general", "Discussion générale"),
        ("direct", "Discussion privée"),
        ("group", "Groupe"),
    ]
    kind = models.CharField(max_length=10, choices=TYPE_CHOICES, default="group")
    title = models.CharField("Titre", max_length=140)
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through="ConversationParticipant",
        related_name="tafita_conversations",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_tafita_conversations",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ["-last_activity"]
        constraints = [
            models.UniqueConstraint(
                fields=["kind"], condition=Q(kind="general"), name="one_general_tafita_conversation"
            )
        ]

    def __str__(self):
        return self.title


class ConversationParticipant(models.Model):
    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name="participant_links"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="conversation_memberships"
    )
    joined_at = models.DateTimeField(auto_now_add=True)
    last_read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["conversation", "user"], name="unique_user_per_tafita_conversation"
            )
        ]
        ordering = ["joined_at"]


class ConversationMessage(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="tafita_messages"
    )
    content = models.CharField("Message", max_length=4000)
    created_at = models.DateTimeField("Envoyé le", auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["created_at", "id"]
        indexes = [models.Index(fields=["conversation", "id"])]

    def __str__(self):
        return f"Message de {self.sender} dans {self.conversation}"


class MemberPaymentSubmission(models.Model):
    STATUS_CHOICES = [
        ("pending", "En attente de vérification"),
        ("approved", "Validé"),
        ("rejected", "Refusé"),
    ]
    METHOD_CHOICES = [
        ("cash", "Espèces"),
        ("mobile_money", "Mobile Money"),
        ("bank", "Virement bancaire"),
        ("other", "Autre"),
    ]
    contribution = models.ForeignKey(
        "contributions.Contribution",
        on_delete=models.PROTECT,
        related_name="member_submissions",
        verbose_name="Cotisation",
    )
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="member_payment_submissions",
    )
    amount = models.PositiveBigIntegerField("Montant déclaré (Ar)")
    method = models.CharField("Mode de paiement", max_length=30, choices=METHOD_CHOICES)
    reference = models.CharField("Référence", max_length=100, blank=True)
    proof = models.FileField(
        "Justificatif (image ou PDF)",
        upload_to="community/payment-proofs/%Y/%m/",
        blank=True,
        null=True,
        validators=[FileExtensionValidator(["jpg", "jpeg", "png", "webp", "pdf"])],
    )
    notes = models.CharField("Note complémentaire", max_length=500, blank=True)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_member_payment_submissions",
    )
    rejection_reason = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status", "-created_at"])]
        verbose_name = "Déclaration de paiement membre"
        verbose_name_plural = "Déclarations de paiement membres"

    def __str__(self):
        return f"{self.amount} Ar — {self.submitted_by} — {self.get_status_display()}"

class Notification(models.Model):
    CATEGORY_CHOICES = [
        ("event", "Événement"),
        ("payment", "Paiement"),
        ("community", "Communauté"),
        ("system", "Système"),
    ]

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tafita_notifications",
        verbose_name="Destinataire",
    )
    title = models.CharField("Titre", max_length=160)
    message = models.TextField("Message", max_length=600)
    category = models.CharField(
        "Catégorie",
        max_length=20,
        choices=CATEGORY_CHOICES,
        default="system",
    )
    url = models.CharField(
        "Lien interne",
        max_length=300,
        blank=True,
    )
    created_at = models.DateTimeField(
        "Créée le",
        auto_now_add=True,
    )
    read_at = models.DateTimeField(
        "Lue le",
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["recipient", "read_at", "-created_at"],
                name="tafita_notif_rec_read_idx",
            ),
        ]
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"

    @property
    def is_read(self):
        return self.read_at is not None

    def __str__(self):
        return f"{self.title} — {self.recipient}"
