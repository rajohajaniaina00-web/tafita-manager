import logging
import os

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.db.models import Q, Sum, Value, BigIntegerField
from django.db.models.functions import Coalesce
from django.shortcuts import render, redirect
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from members.models import Member
from events.models import Event
from contributions.models import Contribution, Payment

logger = logging.getLogger(__name__)

MAX_QUESTION_LENGTH = 1800
MAX_REQUESTS_PER_MINUTE = 8

SYSTEM_INSTRUCTIONS = """
Tu es l'assistant de gestion de l'association TaFiTa intégré à son application.
Réponds en français, de façon concrète, professionnelle, claire et structurée.
Tu reçois uniquement des indicateurs agrégés de l'application, pas les fiches personnelles.
N'invente jamais de chiffres ou de faits. Si les données disponibles ne permettent pas
une réponse, précise cette limite et indique ce que l'administrateur doit vérifier.
Tu peux analyser les indicateurs, proposer des plans d'action, rédiger des brouillons
d'annonces, d'événements, de rappels et de messages. Ne prétends jamais avoir publié,
supprimé, payé, envoyé ou modifié quoi que ce soit : tu n'as pas l'autorisation de modifier
la base de données. Toute action réelle doit être effectuée et confirmée par l'administrateur.
Ne demande pas de mots de passe, clés API, informations bancaires complètes ou autres secrets.
Ne donne pas de noms ou données personnelles : les données disponibles ici sont agrégées.
""".strip()


def can_use_assistant(user):
    if not user.is_authenticated:
        return False
    return (
        user.is_superuser
        or user.is_staff
        or user.has_perm("members.view_member")
        or user.has_perm("events.view_event")
        or user.has_perm("contributions.view_contribution")
    )


def _money(value):
    return f"{int(value or 0):,}".replace(",", " ") + " Ar"


def get_association_snapshot():
    """Build a compact, aggregate-only summary; no member identities are sent to AI."""
    today = timezone.localdate()
    now = timezone.now()

    members_total = Member.objects.count()
    members_active = Member.objects.filter(status="active").count()
    members_inactive = Member.objects.filter(status="inactive").count()

    events_queryset = Event.objects.exclude(status="cancelled")
    events_upcoming = events_queryset.filter(
        Q(date__gte=now) | Q(end_date__gte=now)
    ).count()
    events_total = Event.objects.count()

    expected_total = Contribution.objects.aggregate(total=Sum("amount"))["total"] or 0
    paid_total = Payment.objects.filter(is_voided=False).aggregate(total=Sum("amount"))["total"] or 0

    # Calculate unpaid balance using an annotated query rather than member names/details.
    contributions = Contribution.objects.annotate(
        paid_amount=Coalesce(
            Sum("payments__amount", filter=Q(payments__is_voided=False)),
            Value(0),
            output_field=BigIntegerField(),
        )
    ).values_list("amount", "paid_amount", "due_date")

    remaining_total = 0
    overdue_total = 0
    overdue_count = 0
    unpaid_count = 0
    for amount, paid_amount, due_date in contributions:
        remaining = max(int(amount or 0) - int(paid_amount or 0), 0)
        remaining_total += remaining
        if remaining > 0:
            unpaid_count += 1
            if due_date and due_date < today:
                overdue_total += remaining
                overdue_count += 1

    return {
        "as_of": today.isoformat(),
        "members": {
            "total": members_total,
            "active": members_active,
            "inactive": members_inactive,
        },
        "events": {
            "total": events_total,
            "upcoming_or_ongoing": events_upcoming,
        },
        "contributions": {
            "count": Contribution.objects.count(),
            "expected_total_ariary": int(expected_total),
            "payments_recorded_ariary": int(paid_total),
            "remaining_ariary": remaining_total,
            "unpaid_contributions_count": unpaid_count,
            "overdue_contributions_count": overdue_count,
            "overdue_amount_ariary": overdue_total,
        },
    }


def _make_context_text(snapshot):
    m = snapshot["members"]
    e = snapshot["events"]
    c = snapshot["contributions"]
    return (
        f"Date du relevé : {snapshot['as_of']}\n"
        f"Membres : {m['total']} au total, {m['active']} actifs, {m['inactive']} inactifs.\n"
        f"Événements : {e['total']} au total, {e['upcoming_or_ongoing']} à venir ou en cours.\n"
        f"Cotisations : {c['count']} cotisations; montant attendu {_money(c['expected_total_ariary'])}; "
        f"paiements enregistrés {_money(c['payments_recorded_ariary'])}; "
        f"reste estimé {_money(c['remaining_ariary'])}; "
        f"cotisations avec solde {c['unpaid_contributions_count']}; "
        f"cotisations en retard {c['overdue_contributions_count']}; "
        f"montant en retard {_money(c['overdue_amount_ariary'])}.\n"
        "Confidentialité : ces chiffres sont agrégés; aucune identité ni adresse personnelle n'est fournie."
    )



def _normalise_question(question):
    replacements = {
        "à": "a", "â": "a", "ä": "a",
        "é": "e", "è": "e", "ê": "e", "ë": "e",
        "î": "i", "ï": "i", "ì": "i",
        "ô": "o", "ö": "o", "ò": "o",
        "ù": "u", "û": "u", "ü": "u",
        "ç": "c",
    }
    return question.lower().translate(str.maketrans(replacements))


def _summary_answer(snapshot):
    m = snapshot["members"]
    e = snapshot["events"]
    c = snapshot["contributions"]

    return "\n".join([
        f"RÉSUMÉ DE TAFITA — {snapshot['as_of']}",
        "",
        f"Membres : {m['total']} au total, dont {m['active']} actifs et {m['inactive']} inactifs.",
        f"Événements : {e['total']} au total, dont {e['upcoming_or_ongoing']} à venir ou en cours.",
        f"Cotisations enregistrées : {c['count']}.",
        f"Montant attendu : {_money(c['expected_total_ariary'])}.",
        f"Paiements enregistrés : {_money(c['payments_recorded_ariary'])}.",
        f"Solde restant estimé : {_money(c['remaining_ariary'])}.",
        f"Cotisations en retard : {c['overdue_contributions_count']}.",
        f"Montant total en retard : {_money(c['overdue_amount_ariary'])}.",
        "",
        "À retenir : ces indicateurs donnent une vue générale de l'association. "
        "Vérifie les données et les éventuelles erreurs de saisie avant toute décision.",
    ])


def _overdue_answer(snapshot):
    c = snapshot["contributions"]

    if c["overdue_contributions_count"] == 0:
        status = "Aucune cotisation en retard n'apparaît dans les indicateurs actuels."
    else:
        status = (
            f"{c['overdue_contributions_count']} cotisation(s) présentent un retard, "
            f"pour un montant total calculé de {_money(c['overdue_amount_ariary'])}."
        )

    return "\n".join([
        "SUIVI DES COTISATIONS",
        "",
        status,
        f"Nombre de cotisations avec un solde restant : {c['unpaid_contributions_count']}.",
        "",
        "Plan de suivi proposé :",
        "1. Vérifier les dates d'échéance et les paiements réellement reçus.",
        "2. Rapprocher chaque paiement de la cotisation correspondante.",
        "3. Envoyer un rappel courtois aux personnes concernées par le canal habituel.",
        "4. Enregistrer les paiements confirmés dans TaFiTa Manager.",
        "5. Recalculer les indicateurs après la mise à jour.",
        "",
        "Ce résumé ne contient pas de noms de membres et ne déclenche aucun paiement ni envoi.",
    ])


def _event_draft():
    return "\n".join([
        "BROUILLON D'ANNONCE D'ÉVÉNEMENT",
        "",
        "Titre : [Nom de l'événement]",
        "Date et heure : [Date et heure]",
        "Lieu : [Lieu]",
        "Organisateur ou responsable : [Nom ou fonction]",
        "",
        "Chers membres de TaFiTa,",
        "",
        "Nous avons le plaisir de vous informer de l'organisation de [nom de l'événement], "
        "qui se déroulera le [date] à [heure], à [lieu].",
        "",
        "Objectif : [Présenter brièvement l'objectif de l'activité].",
        "Participants concernés : [Public visé].",
        "Informations pratiques : [Matériel à prévoir, inscription et contact officiel].",
        "",
        "Nous espérons vous retrouver nombreux pour cette activité.",
        "L'équipe TaFiTa",
        "",
        "Complète les champs entre crochets et vérifie les informations avant publication.",
    ])


def _announcement_draft():
    return "\n".join([
        "BROUILLON D'ANNONCE POUR LA COMMUNAUTÉ TAFITA",
        "",
        "Chers membres,",
        "",
        "[Présenter ici l'information ou l'annonce principale.]",
        "",
        "Date : [Date, si nécessaire]",
        "Lieu : [Lieu, si nécessaire]",
        "Informations complémentaires : [Détails utiles]",
        "",
        "Merci à toutes et à tous pour votre participation et votre engagement au sein de TaFiTa.",
        "",
        "L'équipe TaFiTa",
        "",
        "Vérifie et complète les informations avant de diffuser ce message.",
    ])


def _action_plan(snapshot):
    m = snapshot["members"]
    e = snapshot["events"]
    c = snapshot["contributions"]

    steps = [
        "1. Cotisations : comparer les paiements enregistrés avec les reçus et les échéances.",
    ]

    if c["overdue_contributions_count"] > 0:
        steps.append(
            f"2. Retards : vérifier les {c['overdue_contributions_count']} cotisation(s) "
            f"en retard représentant {_money(c['overdue_amount_ariary'])}, puis organiser des rappels courtois."
        )
    else:
        steps.append(
            "2. Retards : continuer à vérifier les échéances pour détecter rapidement les éventuels retards."
        )

    steps.extend([
        f"3. Membres : vérifier que les fiches des {m['total']} membres sont à jour "
        f"({m['active']} actifs, {m['inactive']} inactifs).",
        f"4. Événements : confirmer les informations pratiques et les responsables des "
        f"{e['upcoming_or_ongoing']} événement(s) à venir ou en cours.",
        "5. Suivi : refaire le point sur ces indicateurs chaque semaine et noter les actions réalisées.",
    ])

    return "\n".join([
        "PLAN D'ACTION PROPOSÉ",
        "",
        *steps,
        "",
        "Il s'agit de recommandations automatiques fondées sur les chiffres disponibles, "
        "pas d'actions déjà effectuées.",
    ])


def _local_answer(question, preset, snapshot):
    if preset == "summary":
        return _summary_answer(snapshot)
    if preset == "overdue":
        return _overdue_answer(snapshot)
    if preset == "event_draft":
        return _event_draft()
    if preset == "announcement":
        return _announcement_draft()
    if preset == "action_plan":
        return _action_plan(snapshot)

    q = _normalise_question(question)

    if (
        any(word in q for word in ("annonce", "rediger", "preparer", "brouillon"))
        and any(word in q for word in ("evenement", "activite", "rencontre"))
    ):
        return _event_draft()

    if any(word in q for word in ("annonce", "publication", "communique", "message aux membres")):
        return _announcement_draft()

    if any(word in q for word in ("plan d'action", "plan action", "priorite", "priorites")):
        return _action_plan(snapshot)

    if any(word in q for word in ("membre", "effectif", "actif", "inactive", "inactif")):
        m = snapshot["members"]
        return "\n".join([
            "INDICATEURS DES MEMBRES",
            "",
            f"Nombre total de membres : {m['total']}.",
            f"Membres actifs : {m['active']}.",
            f"Membres inactifs : {m['inactive']}.",
            "",
            "Ces chiffres proviennent des fiches de membres enregistrées dans TaFiTa Manager.",
        ])

    if any(word in q for word in ("evenement", "activite", "rencontre", "agenda")):
        e = snapshot["events"]
        return "\n".join([
            "INDICATEURS DES ÉVÉNEMENTS",
            "",
            f"Nombre total d'événements : {e['total']}.",
            f"Événements à venir ou en cours : {e['upcoming_or_ongoing']}.",
            "",
            "Vérifie les dates, les lieux et les responsables dans le module Événements.",
        ])

    if any(word in q for word in ("cotisation", "paiement", "retard", "impaye", "solde", "ariary")):
        if any(word in q for word in ("retard", "impaye", "impayes", "echeance")):
            return _overdue_answer(snapshot)

        c = snapshot["contributions"]
        return "\n".join([
            "INDICATEURS DES COTISATIONS",
            "",
            f"Nombre de cotisations : {c['count']}.",
            f"Montant attendu : {_money(c['expected_total_ariary'])}.",
            f"Paiements enregistrés : {_money(c['payments_recorded_ariary'])}.",
            f"Solde restant estimé : {_money(c['remaining_ariary'])}.",
            f"Cotisations avec un solde restant : {c['unpaid_contributions_count']}.",
            f"Cotisations en retard : {c['overdue_contributions_count']}.",
            f"Montant en retard : {_money(c['overdue_amount_ariary'])}.",
            "",
            "Les montants sont calculés à partir des cotisations et paiements enregistrés. "
            "Vérifie les justificatifs avant de confirmer un paiement.",
        ])

    if any(word in q for word in ("resume", "situation", "indicateur", "statistique", "association", "tafita")):
        return _summary_answer(snapshot)

    return "\n".join([
        "Bonjour ! Je suis l'assistant local de TaFiTa Manager.",
        "",
        "Je peux analyser les indicateurs de l'association et préparer des brouillons.",
        "Essaie une question comme :",
        "• Combien de membres sont actifs ?",
        "• Combien d'événements sont à venir ?",
        "• Quel est le montant des cotisations en retard ?",
        "• Fais un résumé de la situation de TaFiTa.",
        "• Propose un plan d'action.",
        "• Prépare une annonce d'événement.",
        "",
        "Cette première version fonctionne avec des règles Python. Elle n'utilise pas encore "
        "un modèle génératif capable de comprendre toutes les formulations.",
    ])


@login_required
@require_http_methods(["GET", "POST"])
def assistant_home(request):
    if not can_use_assistant(request.user):
        raise PermissionDenied(
            "L'assistant TaFiTa est réservé aux comptes administratifs autorisés."
        )

    snapshot = get_association_snapshot()
    answer = None
    question = ""

    if request.method == "POST":
        question = request.POST.get("question", "").strip()
        preset = request.POST.get("preset", "").strip()

        if not question and not preset:
            messages.error(request, "Écris une question ou choisis une suggestion.")
        elif len(question) > MAX_QUESTION_LENGTH:
            messages.error(
                request,
                f"La demande est trop longue (maximum {MAX_QUESTION_LENGTH} caractères).",
            )
        else:
            answer = _local_answer(question, preset, snapshot)

    context = {
        "snapshot": snapshot,
        "answer": answer,
        "question": question,
        "api_configured": True,
        "model_name": "assistant-local",
    }
    return render(request, "ai_assistant/home.html", context)
