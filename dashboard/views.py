
from datetime import date

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import (
    Sum,
    F,
    Value,
    Case,
    When,
    BigIntegerField,
)
from django.db.models.functions import Coalesce, TruncMonth
from django.shortcuts import render
from django.utils import timezone

from members.models import Member
from events.models import Event
from contributions.models import Contribution, Payment


def get_last_six_months(today):
    """Retourne les six mois, du plus ancien au plus récent."""
    current = today.replace(day=1)
    months = []

    for _ in range(6):
        months.append(current)

        if current.month == 1:
            current = date(current.year - 1, 12, 1)
        else:
            current = date(current.year, current.month - 1, 1)

    return list(reversed(months))


@login_required
def dashboard_view(request):
    user = request.user

    can_view_members = (
        user.is_superuser or user.has_perm("members.view_member")
    )
    can_view_events = (
        user.is_superuser or user.has_perm("events.view_event")
    )
    can_view_finances = (
        user.is_superuser
        or user.has_perm("contributions.view_contribution")
    )

    # Refuser l'accès aux utilisateurs sans permission utile.
    if not (
        can_view_members
        or can_view_events
        or can_view_finances
    ):
        raise PermissionDenied

    today = timezone.localdate()
    now = timezone.now()

    # Valeurs par défaut pour les utilisateurs sans accès aux données.
    members_total = 0
    members_active = 0
    members_inactive = 0
    recent_members = []

    events_total = 0
    events_upcoming_count = 0
    events_completed_count = 0
    next_events = []

    expected_total = 0
    paid_total = 0
    remaining_total = 0
    overdue_total = 0
    contributions_total = 0
    contributions_paid_count = 0
    contributions_unpaid_count = 0
    recent_payments = []
    month_labels = []
    month_values = []

    # 1. Statistiques des membres.
    if can_view_members:
        members_total = Member.objects.count()
        members_active = Member.objects.filter(
            status="active"
        ).count()
        members_inactive = Member.objects.filter(
            status="inactive"
        ).count()

        recent_members = Member.objects.order_by(
            "-created_at"
        )[:5]

    # 2. Statistiques des événements.
    if can_view_events:
        events_total = Event.objects.count()

        upcoming_events = Event.objects.filter(
            date__gte=now,
            status="planned",
        ).order_by("date")

        events_upcoming_count = upcoming_events.count()

        events_completed_count = sum(
            1
            for event in Event.objects.exclude(
                status="cancelled"
            ).only("date", "end_date", "status")
            if event.current_status == "completed"
        )

        next_events = upcoming_events[:5]

    # 3. Données financières : requêtes exécutées uniquement
    # pour les utilisateurs disposant de la permission financière.
    if can_view_finances:
        contributions_with_payments = Contribution.objects.annotate(
            paid_amount=Coalesce(
                Sum("payments__amount"),
                Value(0),
                output_field=BigIntegerField(),
            )
        ).annotate(
            remaining=Case(
                When(
                    paid_amount__gte=F("amount"),
                    then=Value(0),
                ),
                default=F("amount") - F("paid_amount"),
                output_field=BigIntegerField(),
            )
        )

        expected_total = (
            Contribution.objects.aggregate(
                total=Sum("amount")
            )["total"] or 0
        )

        paid_total = (
            Payment.objects.aggregate(
                total=Sum("amount")
            )["total"] or 0
        )

        remaining_total = (
            contributions_with_payments.aggregate(
                total=Sum("remaining")
            )["total"] or 0
        )

        overdue_total = (
            contributions_with_payments.filter(
                due_date__lt=today,
                remaining__gt=0,
            ).aggregate(total=Sum("remaining"))["total"] or 0
        )

        contributions_total = Contribution.objects.count()

        contributions_paid_count = (
            contributions_with_payments.filter(
                remaining=0
            ).count()
        )

        contributions_unpaid_count = (
            contributions_with_payments.filter(
                remaining__gt=0
            ).count()
        )

        recent_payments = Payment.objects.select_related(
            "contribution",
            "contribution__member",
        ).order_by("-payment_date", "-created_at")[:5]

        # Graphique des six derniers mois.
        months = get_last_six_months(today)
        first_month = months[0]

        monthly_payments = (
            Payment.objects.filter(
                payment_date__gte=first_month
            )
            .annotate(month=TruncMonth("payment_date"))
            .values("month")
            .annotate(total=Sum("amount"))
            .order_by("month")
        )

        payments_by_month = {
            row["month"].replace(day=1): row["total"]
            for row in monthly_payments
        }

        month_labels = [
            month.strftime("%m/%Y")
            for month in months
        ]

        month_values = [
            int(payments_by_month.get(month, 0))
            for month in months
        ]

    context = {
        "today": today,
        "can_view_members": can_view_members,
        "can_view_events": can_view_events,
        "can_view_finances": can_view_finances,
        "members_total": members_total,
        "members_active": members_active,
        "members_inactive": members_inactive,
        "events_total": events_total,
        "events_upcoming_count": events_upcoming_count,
        "events_completed_count": events_completed_count,
        "expected_total": expected_total,
        "paid_total": paid_total,
        "remaining_total": remaining_total,
        "overdue_total": overdue_total,
        "contributions_total": contributions_total,
        "contributions_paid_count": contributions_paid_count,
        "contributions_unpaid_count": contributions_unpaid_count,
        "recent_members": recent_members,
        "recent_payments": recent_payments,
        "next_events": next_events,
        "month_labels": month_labels,
        "month_values": month_values,
    }

    return render(request, "dashboard/index.html", context)
