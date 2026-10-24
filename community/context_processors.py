def tafita_notifications(request):
    """Expose le nombre de notifications non lues dans les menus."""
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {"tafita_unread_notification_count": 0}

    from .models import Notification

    count = Notification.objects.filter(
        recipient=user,
        read_at__isnull=True,
    ).count()

    return {"tafita_unread_notification_count": count}
