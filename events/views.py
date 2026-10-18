
from datetime import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import Event


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
                    Event.objects.create(
                        title=title,
                        description=description,
                        date=start,
                        end_date=end,
                        location=location,
                        responsible=responsible,
                        status="planned",
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
    """Modifier un événement existant."""
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
                    event.title = title
                    event.description = description
                    event.date = start
                    event.end_date = end
                    event.location = location
                    event.responsible = responsible

                    # Le statut reste manuel uniquement pour l'annulation.
                    event.status = "cancelled" if cancelled else "planned"

                    event.save()

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