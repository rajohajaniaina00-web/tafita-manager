from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.db import transaction
from django.utils import timezone
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import ContributionForm, PaymentForm
from .models import Contribution, Payment


@login_required
@permission_required("contributions.view_contribution", raise_exception=True)
def contribution_list(request):
    query = request.GET.get("q", "").strip()

    contributions = Contribution.objects.select_related(
        "member"
    ).prefetch_related("payments")

    if query:
        contributions = contributions.filter(
            title__icontains=query
        ) | contributions.filter(
            member__first_name__icontains=query
        ) | contributions.filter(
            member__last_name__icontains=query
        )

    return render(
        request,
        "contributions/list.html",
        {
            "contributions": contributions,
            "query": query,
        },
    )


@login_required
@permission_required("contributions.add_contribution", raise_exception=True)
def contribution_create(request):
    form = ContributionForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(
            request,
            "La cotisation a été ajoutée avec succès.",
        )
        return redirect("contribution_list")

    return render(
        request,
        "contributions/form.html",
        {
            "form": form,
            "page_title": "Ajouter une cotisation",
        },
    )


@login_required
@permission_required("contributions.add_payment", raise_exception=True)
def payment_create(request, pk):
    contribution = get_object_or_404(
        Contribution.objects.select_related("member").prefetch_related(
            "payments"
        ),
        pk=pk,
    )

    if contribution.remaining_amount <= 0:
        messages.info(
            request,
            "Cette cotisation est déjà entièrement payée.",
        )
        return redirect("contribution_list")

    form = PaymentForm(
        request.POST or None,
        contribution=contribution,
    )

    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            locked_contribution = get_object_or_404(
                Contribution.objects.select_for_update(),
                pk=pk,
            )

            # Recalculer le solde à partir des paiements enregistrés.
            locked_contribution.refresh_from_db()

            payment_form = PaymentForm(
                request.POST,
                contribution=locked_contribution,
            )

            if payment_form.is_valid():
                payment = payment_form.save(commit=False)
                payment.contribution = locked_contribution
                payment.save()

                messages.success(
                    request,
                    "Le paiement a été enregistré avec succès.",
                )
                return redirect("contribution_list")

            form = payment_form

    return render(
        request,
        "contributions/payment_form.html",
        {
            "form": form,
            "contribution": contribution,
        },
    )

@login_required
@permission_required("contributions.delete_payment", raise_exception=True)
@require_POST
def payment_delete(request, pk):
    reason = request.POST.get("reason", "").strip()[:300]
    if not reason:
        messages.error(
            request,
            "Le motif d'annulation est obligatoire. Aucun changement n'a été effectué.",
        )
        return redirect("contribution_list")

    with transaction.atomic():
        payment = get_object_or_404(
            Payment.objects.select_for_update().select_related("contribution"),
            pk=pk,
        )

        if payment.is_voided:
            messages.info(request, "Ce paiement est déjà annulé.")
            return redirect("contribution_list")

        payment.is_voided = True
        payment.voided_at = timezone.now()
        payment.voided_by = request.user
        payment.void_reason = reason
        payment.save(update_fields=[
            "is_voided", "voided_at", "voided_by", "void_reason"
        ])

    messages.success(
        request,
        "Paiement annulé. Son enregistrement et son historique sont conservés.",
    )
    return redirect("contribution_list")
