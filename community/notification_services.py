from members.models import Member
from .models import Notification


def notify_user(*, recipient, title, message, category, url=""):
    """Créer une notification pour un destinataire précis."""
    if recipient is None:
        return None

    return Notification.objects.create(
        recipient=recipient,
        title=title[:160],
        message=message[:600],
        category=category,
        url=url[:300],
    )


def notify_active_members(*, title, message, category="event", url="",
                          exclude_user_id=None):
    """Notifier uniquement les membres actifs disposant d'un compte."""
    users = Member.objects.filter(
        status="active",
        user__isnull=False,
    ).values_list("user_id", flat=True).distinct()

    if exclude_user_id is not None:
        users = users.exclude(user_id=exclude_user_id)

    notifications = [
        Notification(
            recipient_id=user_id,
            title=title[:160],
            message=message[:600],
            category=category,
            url=url[:300],
        )
        for user_id in users
    ]

    return Notification.objects.bulk_create(notifications, batch_size=500)
