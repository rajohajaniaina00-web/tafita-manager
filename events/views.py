
from datetime import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import Event
from community.notification_services import notify_active_members


@login_required
@permission_required("events.view_event", raise_exception=True)
def events_list(request):
    """Afficher la liste des événements."""
    events = Event.objects.all()

    return render(
        request,
        "events/list.html",
        {"events": events},
    )


@login_required
@permission_required("events.add_event", raise_exception=True)
def event_create(request):
    """Ajouter un nouvel événement."""
    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        description = request.POST.get("description", "").strip()
        date = request.POST.get("date", "").strip()
        end_date = request.POST.get("end_date", "").strip()
        location = request.POST.get("location", "").strip()
        responsible = request.POST.get("responsible", "").strip()

        if not all([title, date, end_date, location, responsible]):
            messages.error(
                request,
                "Veuillez remplir tous les champs obligatoires.",
            )
        else:
            try:
                start = datetime.fromisoformat(date)
                end = datetime.fromisoformat(end_date)

                current_timezone = timezone.get_current_timezone()

                if timezone.is_naive(start):
                    start = timezone.make_aware(
                        start, current_timezone
                    )

                if timezone.is_naive(end):
                    end = timezone.make_aware(
                        end, current_timezone
                    )

                if end <= start:
                    messages.error(
                        request,
                        "La date de fin doit être après la date de début.",
                    )
                else:
                    event = Event.objects.create(
                        title=title,
                        description=description,
                        date=start,
                        end_date=end,
                        location=location,
                        responsible=responsible,
                        status="planned",
                    )

                    event_date = timezone.localtime(event.date).strftime("%d/%m/%Y à %H:%M")
                    notify_active_members(
                        title=f"Nouvel événement : {event.title}",
                        message=(f"Une activité est prévue le {event_date} à "
                                 f"{event.location}. Consultez ses détails dans TaFiTa."),
                        category="event",
                        url=reverse("community_event_detail", args=[event.pk]),
                    )

                    messages.success(
                        request,
                        "L'événement a été ajouté avec succès.",
                    )

                    return redirect("events_list")

            except (ValueError, TypeError, OverflowError):
                messages.error(
                    request,
                    "Veuillez vérifier les dates et heures saisies.",
                )

    return render(
        request,
        "events/form.html",
        {
            "event": None,
            "editing": False,
        },
    )


@login_required
@permission_required("events.change_event", raise_exception=True)
def event_update(request, pk):
    """Modifier un événement et notifier les membres si nécessaire."""
    event = get_object_or_404(Event, pk=pk)

    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        description = request.POST.get("description", "").strip()
        date = request.POST.get("date", "").strip()
        end_date = request.POST.get("end_date", "").strip()
        location = request.POST.get("location", "").strip()
        responsible = request.POST.get("responsible", "").strip()
        cancelled = request.POST.get("cancelled") == "on"

        if not all([title, date, end_date, location, responsible]):
            messages.error(
                request,
                "Veuillez remplir tous les champs obligatoires.",
            )
        else:
            try:
                start_date = datetime.fromisoformat(date)
                finish_date = datetime.fromisoformat(end_date)
                current_timezone = timezone.get_current_timezone()

                if timezone.is_naive(start_date):
                    start_date = timezone.make_aware(
                        start_date, current_timezone
                    )
                if timezone.is_naive(finish_date):
                    finish_date = timezone.make_aware(
                        finish_date, current_timezone
                    )

                if finish_date <= start_date:
                    messages.error(
                        request,
                        "La date de fin doit être après la date de début.",
                    )
                else:
                    was_cancelled = event.status == "cancelled"
                    new_status = "cancelled" if cancelled else "planned"

                    changed = any([
                        event.title != title,
                        event.description != description,
                        event.date != start_date,
                        event.end_date != finish_date,
                        event.location != location,
                        event.responsible != responsible,
                        event.status != new_status,
                    ])

                    event.title = title
                    event.description = description
                    event.date = start_date
                    event.end_date = finish_date
                    event.location = location
                    event.responsible = responsible
                    event.status = new_status
                    event.save()

                    event_url = reverse(
                        "community_event_detail",
                        args=[event.pk],
                    )
                    event_date = timezone.localtime(
                        event.date
                    ).strftime("%d/%m/%Y à %H:%M")

                    if cancelled and not was_cancelled:
                        notify_active_members(
                            title=f"Événement annulé : {event.title}",
                            message=(
                                f"L'activité prévue le {event_date} "
                                f"à {event.location} a été annulée."
                            ),
                            category="event",
                            url=event_url,
                        )
                    elif changed and not cancelled:
                        notify_active_members(
                            title=f"Événement modifié : {event.title}",
                            message=(
                                f"Les informations de l'activité prévue "
                                f"le {event_date} à {event.location} "
                                "ont été mises à jour."
                            ),
                            category="event",
                            url=event_url,
                        )

                    messages.success(
                        request,
                        "L'événement a été modifié avec succès.",
                    )
                    return redirect("events_list")

            except (ValueError, TypeError, OverflowError):
                messages.error(
                    request,
                    "Veuillez vérifier les dates et heures saisies.",
                )

    return render(
        request,
        "events/form.html",
        {
            "event": event,
            "editing": True,
        },
    )

@login_required
@permission_required("events.delete_event", raise_exception=True)
@require_POST
def event_delete(request, pk):
    """Supprimer un événement uniquement via une requête POST."""
    event = get_object_or_404(Event, pk=pk)
    event.delete()

    messages.success(
        request,
        "L'événement a été supprimé.",
    )

    return redirect("events_list")