import secrets
from datetime import timedelta
from functools import wraps

from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Count, Exists, OuterRef, Q, Sum
from django.http import JsonResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from events.models import Event
from contributions.models import Contribution, Payment
from members.models import Member
from .forms import (
    CommunityPostForm,
    ConversationMessageForm,
    EventCommentForm,
    GroupConversationForm,
    MemberLoginForm,
    MemberRegistrationForm,
    MemberPaymentSubmissionForm,
    PostCommentForm,
)
from .models import (
    CommunityPost,
    Conversation,
    ConversationMessage,
    ConversationParticipant,
    EventComment,
    EventReaction,
    MemberInvitation,
    Notification,
    MemberPaymentSubmission,
    PostComment,
    PostReaction,
)

from .notification_services import notify_user

User = get_user_model()


def has_admin_access(user):
    if not user.is_authenticated:
        return False
    return bool(
        user.is_superuser
        or user.has_perm("members.view_member")
        or user.has_perm("members.change_member")
        or user.has_perm("events.view_event")
        or user.has_perm("events.add_event")
        or user.has_perm("contributions.view_contribution")
        or user.has_perm("contributions.add_contribution")
    )


def has_community_access(user):
    if not user.is_authenticated or not user.is_active:
        return False
    if has_admin_access(user) or user.is_staff:
        return True
    try:
        return user.member_profile.status == "active"
    except Member.DoesNotExist:
        return False


def community_required(view_func):
    @login_required
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        if not has_community_access(request.user):
            messages.warning(
                request,
                "Votre compte n’est pas associé à un membre actif. Contactez l’administration TaFiTa.",
            )
            logout(request)
            return redirect("member_login")
        return view_func(request, *args, **kwargs)
    return wrapped


def admin_required(view_func):
    @login_required
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        if not (has_admin_access(request.user) or request.user.is_staff or request.user.is_superuser):
            raise PermissionDenied("Cette fonctionnalité est réservée à l’administration.")
        return view_func(request, *args, **kwargs)
    return wrapped


def eligible_community_users():
    """Active Django users who are active members or authorized administrators."""
    candidates = User.objects.filter(is_active=True).select_related("member_profile")
    allowed_ids = []
    for candidate in candidates:
        if has_community_access(candidate):
            allowed_ids.append(candidate.pk)
    return User.objects.filter(pk__in=allowed_ids, is_active=True).order_by("username")


def ensure_general_conversation():
    conversation, _ = Conversation.objects.get_or_create(
        kind="general",
        defaults={"title": "Discussion générale"},
    )
    current_ids = set(
        ConversationParticipant.objects.filter(conversation=conversation)
        .values_list("user_id", flat=True)
    )
    new_ids = set(eligible_community_users().values_list("id", flat=True)) - current_ids
    if new_ids:
        ConversationParticipant.objects.bulk_create(
            [ConversationParticipant(conversation=conversation, user_id=user_id) for user_id in new_ids],
            ignore_conflicts=True,
        )
    return conversation


def safe_conversation_title(conversation, user):
    if conversation.kind in ("general", "group"):
        return conversation.title
    other = conversation.participants.exclude(pk=user.pk).first()
    if other:
        display = (f"{other.first_name} {other.last_name}".strip()) or other.username
        return display
    return "Discussion privée"


def member_login_view(request):
    if request.user.is_authenticated and has_community_access(request.user):
        return redirect("community_feed")
    form = MemberLoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = authenticate(
            request,
            username=form.cleaned_data["username"].strip(),
            password=form.cleaned_data["password"],
        )
        if user is None:
            form.add_error(None, "Nom d’utilisateur ou mot de passe incorrect.")
        elif has_admin_access(user) or user.is_staff:
            form.add_error(None, "Ce compte dispose de droits d’administration. Connectez-vous depuis l’accès administrateur.")
        elif not has_community_access(user):
            form.add_error(None, "Ce compte n’est pas associé à une fiche de membre active. Contactez l’administration.")
        else:
            login(request, user)
            return redirect("community_feed")
    return render(request, "community/member_login.html", {"form": form})


def member_register_view(request):
    if request.user.is_authenticated:
        return redirect("community_feed" if has_community_access(request.user) else "member_login")

    form = MemberRegistrationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        code = form.cleaned_data["activation_code"].strip()
        username = form.cleaned_data["username"].strip()
        email = form.cleaned_data["email"].strip()
        password1 = form.cleaned_data["password1"]
        password2 = form.cleaned_data["password2"]

        if password1 != password2:
            form.add_error("password2", "Les deux mots de passe ne correspondent pas.")
        elif User.objects.filter(username__iexact=username).exists():
            form.add_error("username", "Ce nom d’utilisateur est déjà utilisé.")
        else:
            try:
                with transaction.atomic():
                    invitation = (
                        MemberInvitation.objects.select_for_update()
                        .select_related("member")
                        .get(code=code)
                    )
                    member = Member.objects.select_for_update().get(pk=invitation.member_id)

                    if invitation.used_at is not None:
                        raise ValidationError("Ce code a déjà été utilisé.")
                    if invitation.expires_at <= timezone.now():
                        raise ValidationError("Ce code a expiré. Demandez un nouveau code à l’administration.")
                    if member.user_id is not None:
                        raise ValidationError("Cette fiche membre possède déjà un compte.")
                    if member.status != "active":
                        raise ValidationError("Cette fiche membre n’est pas active.")
                    if member.email and email and member.email.casefold() != email.casefold():
                        raise ValidationError("Utilisez l’adresse e-mail enregistrée par l’association ou contactez l’administration.")

                    final_email = member.email or email
                    user_candidate = User(username=username, email=final_email)
                    try:
                        validate_password(password1, user=user_candidate)
                    except ValidationError as exc:
                        raise ValidationError(exc.messages)

                    user = User.objects.create_user(
                        username=username,
                        email=final_email,
                        password=password1,
                        first_name=member.first_name,
                        last_name=member.last_name,
                    )
                    member.user = user
                    member.save(update_fields=["user", "updated_at"])
                    invitation.used_at = timezone.now()
                    invitation.save(update_fields=["used_at"])
            except MemberInvitation.DoesNotExist:
                form.add_error("activation_code", "Code d’activation invalide.")
            except ValidationError as exc:
                form.add_error(None, " ".join(exc.messages))
            except IntegrityError:
                form.add_error(None, "Cette fiche membre ou ce nom d’utilisateur est déjà associé à un compte.")
            else:
                login(request, user)
                messages.success(request, "Votre compte TaFiTa a été créé. Bienvenue !")
                return redirect("community_feed")

    return render(request, "community/member_register.html", {"form": form})


@login_required
@require_POST
def member_logout_view(request):
    logout(request)
    messages.success(request, "Vous êtes déconnecté.")
    return redirect("member_login")


@community_required
def community_feed(request):
    approved_posts = (
        CommunityPost.objects.filter(status="approved")
        .select_related("author")
        .annotate(
            love_count=Count("reactions", distinct=True),
            comment_count=Count("comments", distinct=True),
            user_loved=Exists(PostReaction.objects.filter(post_id=OuterRef("pk"), user=request.user)),
        )[:40]
    )
    now = timezone.now()
    upcoming_events = (
        Event.objects.exclude(status="cancelled")
        .filter(Q(date__gte=now) | Q(end_date__gte=now))
        .select_related()
        .annotate(
            love_count=Count("community_reactions", distinct=True),
            comment_count=Count("community_comments", distinct=True),
            user_loved=Exists(EventReaction.objects.filter(event_id=OuterRef("pk"), user=request.user)),
        ).order_by("date")[:5]
    )
    own_pending_posts = CommunityPost.objects.filter(author=request.user, status="pending")[:5]
    form = CommunityPostForm()
    return render(request, "community/feed.html", {
        "posts": approved_posts,
        "upcoming_events": upcoming_events,
        "post_form": form,
        "own_pending_posts": own_pending_posts,
    })


@community_required
@require_POST
def create_post(request):
    form = CommunityPostForm(request.POST, request.FILES)
    if form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.status = "approved" if (has_admin_access(request.user) or request.user.is_staff) else "pending"
        if post.status == "approved":
            post.moderated_at = timezone.now()
            post.moderated_by = request.user
        post.save()
        if post.status == "pending":
            messages.success(request, "Votre publication a été envoyée à l’administration pour validation.")
        else:
            messages.success(request, "Votre publication a été publiée.")
    else:
        messages.error(request, "Votre publication est invalide. Ajoutez un texte ou une image et vérifiez le fichier joint.")
    return redirect("community_feed")


@community_required
@require_POST
def toggle_post_love(request, post_id):
    post = get_object_or_404(CommunityPost, pk=post_id, status="approved")
    reaction, created = PostReaction.objects.get_or_create(post=post, user=request.user)
    if not created:
        reaction.delete()
    return redirect(request.POST.get("next") or "community_feed")


@community_required
@require_POST
def add_post_comment(request, post_id):
    post = get_object_or_404(CommunityPost, pk=post_id, status="approved")
    form = PostCommentForm(request.POST)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.post = post
        comment.author = request.user
        comment.save()
    else:
        messages.error(request, "Le commentaire doit contenir entre 1 et 1 500 caractères.")
    return redirect("community_feed")


@community_required
def event_detail(request, event_id):
    event = get_object_or_404(Event, pk=event_id)
    comments = event.community_comments.select_related("author")[:100]
    user_loved = EventReaction.objects.filter(event=event, user=request.user).exists()
    return render(request, "community/event_detail.html", {
        "event": event,
        "comments": comments,
        "comment_form": EventCommentForm(),
        "love_count": event.community_reactions.count(),
        "user_loved": user_loved,
    })


@community_required
@require_POST
def toggle_event_love(request, event_id):
    event = get_object_or_404(Event.objects.exclude(status="cancelled"), pk=event_id)
    reaction, created = EventReaction.objects.get_or_create(event=event, user=request.user)
    if not created:
        reaction.delete()
    return redirect("community_event_detail", event_id=event.pk)


@community_required
@require_POST
def add_event_comment(request, event_id):
    event = get_object_or_404(Event, pk=event_id)
    form = EventCommentForm(request.POST)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.event = event
        comment.author = request.user
        comment.save()
    else:
        messages.error(request, "Le commentaire est vide ou trop long.")
    return redirect("community_event_detail", event_id=event.pk)


@admin_required
def activation_codes(request):
    generated_code = None
    if request.method == "POST":
        member_id = request.POST.get("member_id", "").strip()
        member = get_object_or_404(Member, pk=member_id)
        if member.user_id:
            messages.error(request, "Ce membre possède déjà un compte.")
        elif member.status != "active":
            messages.error(request, "Activez d’abord la fiche membre avant de créer une invitation.")
        else:
            generated_code = secrets.token_urlsafe(18)
            MemberInvitation.objects.update_or_create(
                member=member,
                defaults={
                    "code": generated_code,
                    "expires_at": timezone.now() + timedelta(days=7),
                    "used_at": None,
                    "created_by": request.user,
                },
            )
            messages.success(request, "Code créé. Copiez-le et transmettez-le directement au membre concerné.")
    available_members = Member.objects.filter(user__isnull=True, status="active").order_by("last_name", "first_name")
    invitations = MemberInvitation.objects.select_related("member").order_by("-created_at")[:30]
    linked_accounts = Member.objects.filter(user__isnull=False).select_related("user").order_by("last_name", "first_name")
    return render(request, "community/activation_codes.html", {
        "available_members": available_members,
        "invitations": invitations,
        "linked_accounts": linked_accounts,
        "generated_code": generated_code,
        "now": timezone.now(),
    })


@admin_required
def post_moderation(request):
    pending_posts = CommunityPost.objects.filter(status="pending").select_related("author").order_by("created_at")
    return render(request, "community/post_moderation.html", {"pending_posts": pending_posts})


@admin_required
@require_POST
def moderate_post(request, post_id, action):
    post = get_object_or_404(CommunityPost, pk=post_id, status="pending")
    if action not in {"approve", "reject"}:
        raise Http404
    post.status = "approved" if action == "approve" else "rejected"
    post.moderated_at = timezone.now()
    post.moderated_by = request.user
    post.moderation_note = request.POST.get("moderation_note", "").strip()[:300]
    post.save(update_fields=["status", "moderated_at", "moderated_by", "moderation_note", "updated_at"])
    messages.success(request, "Publication approuvée." if action == "approve" else "Publication refusée.")
    return redirect("community_post_moderation")


@community_required
def discussions(request):
    general = ensure_general_conversation()
    if not ConversationParticipant.objects.filter(conversation=general, user=request.user).exists():
        ConversationParticipant.objects.get_or_create(conversation=general, user=request.user)
    conversations = (
        Conversation.objects.filter(participants=request.user)
        .prefetch_related("participants")
        .order_by("-last_activity")
    )
    conversation_rows = [
        {"conversation": conversation, "display_title": safe_conversation_title(conversation, request.user)}
        for conversation in conversations
    ]
    contacts = eligible_community_users().exclude(pk=request.user.pk)
    group_form = GroupConversationForm(eligible_users=contacts)
    return render(request, "community/discussions.html", {
        "conversation_rows": conversation_rows,
        "contacts": contacts,
        "group_form": group_form,
    })


@community_required
@require_POST
def create_group_conversation(request):
    contacts = eligible_community_users().exclude(pk=request.user.pk)
    form = GroupConversationForm(request.POST, eligible_users=contacts)
    if not form.is_valid():
        messages.error(request, "Vérifiez le nom du groupe et les participants sélectionnés.")
        return redirect("community_discussions")
    selected = list(form.cleaned_data["participants"])
    if not selected:
        messages.error(request, "Sélectionnez au moins un autre participant.")
        return redirect("community_discussions")
    conversation = Conversation.objects.create(
        kind="group", title=form.cleaned_data["title"].strip(), created_by=request.user
    )
    ConversationParticipant.objects.bulk_create([
        ConversationParticipant(conversation=conversation, user=user)
        for user in [request.user, *selected]
    ], ignore_conflicts=True)
    messages.success(request, "Groupe de discussion créé.")
    return redirect("community_conversation", conversation_id=conversation.pk)


@community_required
@require_POST
def start_direct_conversation(request, user_id):
    target = get_object_or_404(eligible_community_users(), pk=user_id)
    if target.pk == request.user.pk:
        messages.error(request, "Vous ne pouvez pas démarrer une conversation avec vous-même.")
        return redirect("community_discussions")
    conversation = (
        Conversation.objects.filter(kind="direct", participants=request.user)
        .filter(participants=target)
        .annotate(participant_count=Count("participant_links", distinct=True))
        .filter(participant_count=2)
        .first()
    )
    if conversation is None:
        with transaction.atomic():
            conversation = Conversation.objects.create(
                kind="direct", title="Discussion privée", created_by=request.user
            )
            ConversationParticipant.objects.bulk_create([
                ConversationParticipant(conversation=conversation, user=request.user),
                ConversationParticipant(conversation=conversation, user=target),
            ])
    return redirect("community_conversation", conversation_id=conversation.pk)


def _get_participant_conversation(request, conversation_id):
    conversation = get_object_or_404(Conversation, pk=conversation_id)
    if not ConversationParticipant.objects.filter(conversation=conversation, user=request.user).exists():
        raise PermissionDenied("Vous ne participez pas à cette discussion.")
    return conversation


@community_required
def conversation_detail(request, conversation_id):
    conversation = _get_participant_conversation(request, conversation_id)
    if conversation.kind == "general":
        ensure_general_conversation()
    form = ConversationMessageForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        message = form.save(commit=False)
        message.conversation = conversation
        message.sender = request.user
        message.save()
        conversation.last_activity = message.created_at
        conversation.save(update_fields=["last_activity"])
        return redirect("community_conversation", conversation_id=conversation.pk)
    recent_messages = list(
        conversation.messages.select_related("sender").order_by("-id")[:80]
    )
    recent_messages.reverse()
    ConversationParticipant.objects.filter(conversation=conversation, user=request.user).update(last_read_at=timezone.now())
    return render(request, "community/conversation.html", {
        "conversation": conversation,
        "display_title": safe_conversation_title(conversation, request.user),
        "messages_list": recent_messages,
        "message_form": form,
        "last_message_id": recent_messages[-1].id if recent_messages else 0,
    })


@community_required
def conversation_messages_json(request, conversation_id):
    conversation = _get_participant_conversation(request, conversation_id)
    try:
        after_id = max(0, int(request.GET.get("after", "0")))
    except (TypeError, ValueError):
        after_id = 0
    message_rows = conversation.messages.filter(id__gt=after_id).select_related("sender").order_by("id")[:100]
    data = []
    for item in message_rows:
        sender_name = (f"{item.sender.first_name} {item.sender.last_name}".strip()) or item.sender.username
        data.append({
            "id": item.id,
            "sender": sender_name,
            "username": item.sender.username,
            "content": item.content,
            "created_at": timezone.localtime(item.created_at).strftime("%d/%m/%Y %H:%M"),
            "is_mine": item.sender_id == request.user.id,
        })
    return JsonResponse({"messages": data})


@community_required
def my_contributions(request):
    try:
        member = request.user.member_profile
    except Member.DoesNotExist:
        if has_admin_access(request.user) or request.user.is_staff:
            return redirect("contribution_list")
        raise PermissionDenied("Aucune fiche membre n’est associée à ce compte.")
    contributions = Contribution.objects.filter(member=member).prefetch_related("payments").order_by("-created_at")
    submissions = MemberPaymentSubmission.objects.filter(submitted_by=request.user).select_related("contribution").order_by("-created_at")[:30]
    return render(request, "community/my_contributions.html", {
        "member": member,
        "contributions": contributions,
        "submissions": submissions,
    })


@community_required
@require_POST
def submit_member_payment(request, contribution_id):
    try:
        member = request.user.member_profile
    except Member.DoesNotExist:
        raise PermissionDenied("Une fiche membre est nécessaire pour déclarer un paiement.")
    contribution = get_object_or_404(
        Contribution.objects.select_related("member").prefetch_related("payments"),
        pk=contribution_id,
        member=member,
    )
    form = MemberPaymentSubmissionForm(request.POST, request.FILES)
    if not form.is_valid():
        messages.error(request, "Vérifiez le montant, le mode de paiement et le justificatif.")
        return redirect("community_my_contributions")

    already_pending = MemberPaymentSubmission.objects.filter(
        contribution=contribution, status="pending"
    ).aggregate(total=Sum("amount"))["total"] or 0
    available = max(contribution.remaining_amount - already_pending, 0)
    if form.cleaned_data["amount"] > available:
        messages.error(
            request,
            f"Le montant déclaré dépasse le solde disponible pour cette cotisation ({available} Ar).",
        )
        return redirect("community_my_contributions")

    submission = form.save(commit=False)
    submission.contribution = contribution
    submission.submitted_by = request.user
    submission.status = "pending"
    submission.save()
    messages.success(
        request,
        "Votre déclaration a été envoyée. Elle sera prise en compte après vérification par l’administration.",
    )
    return redirect("community_my_contributions")


@admin_required
def payment_submission_moderation(request):
    submissions = MemberPaymentSubmission.objects.select_related(
        "contribution", "contribution__member", "submitted_by", "reviewed_by"
    ).filter(status="pending").order_by("created_at")
    return render(request, "community/payment_moderation.html", {"submissions": submissions})


@admin_required
@require_POST
def review_member_payment(request, submission_id, action):
    if action not in {"approve", "reject"}:
        raise Http404
    with transaction.atomic():
        submission = get_object_or_404(
            MemberPaymentSubmission.objects.select_for_update().select_related("contribution"),
            pk=submission_id,
            status="pending",
        )
        contribution = Contribution.objects.select_for_update().get(pk=submission.contribution_id)
        if action == "approve":
            remaining = contribution.remaining_amount
            if submission.amount > remaining:
                messages.error(
                    request,
                    f"Validation impossible : le solde restant est de {remaining} Ar. Vérifiez cette déclaration.",
                )
                return redirect("community_payment_moderation")
            proof_note = f" Justificatif joint : {submission.proof.name}." if submission.proof else ""
            note = f"Paiement validé depuis l’espace membre par {request.user.username}.{proof_note}"
            if submission.notes:
                note += f" Note du membre : {submission.notes}"
            Payment.objects.create(
                contribution=contribution,
                amount=submission.amount,
                payment_date=timezone.localdate(),
                method=submission.method,
                reference=submission.reference,
                notes=note[:2000],
            )
            submission.status = "approved"
            success_text = "Paiement vérifié et ajouté à l’historique de la cotisation."
        else:
            submission.status = "rejected"
            submission.rejection_reason = request.POST.get("rejection_reason", "").strip()[:300]
            success_text = "Déclaration de paiement refusée."
        submission.reviewed_at = timezone.now()
        submission.reviewed_by = request.user
        submission.save(update_fields=["status", "rejection_reason", "reviewed_at", "reviewed_by"])
        if submission.submitted_by_id:
            amount_label = f"{submission.amount:,}".replace(",", " ")

            if action == "approve":
                notification_title = "Paiement validé"
                notification_message = (
                    f"Votre déclaration de paiement de {amount_label} Ar "
                    "a été vérifiée et validée."
                )
            else:
                notification_title = "Déclaration de paiement refusée"
                notification_message = (
                    f"Votre déclaration de paiement de {amount_label} Ar "
                    "n'a pas été validée."
                )
                if submission.rejection_reason:
                    notification_message += (
                        f" Motif : {submission.rejection_reason}"
                    )

            notify_user(
                recipient=submission.submitted_by,
                title=notification_title,
                message=notification_message,
                category="payment",
                url=reverse("community_my_contributions"),
            )
    messages.success(request, success_text)
    return redirect("community_payment_moderation")


@admin_required
@require_POST
def delete_member_account(request, member_id):
    member = get_object_or_404(Member.objects.select_related("user"), pk=member_id)
    user = member.user
    if user is None:
        messages.info(request, "Cette fiche membre n’a pas de compte utilisateur à supprimer.")
        return redirect("community_activation_codes")
    if user.is_superuser or user.is_staff:
        messages.error(request, "Pour protéger l’administration, un compte administrateur ne peut pas être supprimé depuis cette page.")
        return redirect("community_activation_codes")
    username = user.username
    user.delete()
    messages.success(request, f"Le compte {username} a été supprimé. La fiche membre est conservée sans compte associé.")
    return redirect("community_activation_codes")


@community_required
def notification_list(request):
    """Afficher les notifications du seul utilisateur connecté."""
    notifications = Notification.objects.filter(
        recipient=request.user
    )[:100]
    unread_count = Notification.objects.filter(
        recipient=request.user,
        read_at__isnull=True,
    ).count()

    return render(
        request,
        "community/notifications.html",
        {
            "notifications": notifications,
            "unread_count": unread_count,
        },
    )


@community_required
@require_POST
def notification_mark_read(request, notification_id):
    """Marquer comme lue une notification appartenant à l'utilisateur."""
    notification = get_object_or_404(
        Notification,
        pk=notification_id,
        recipient=request.user,
    )

    if notification.read_at is None:
        notification.read_at = timezone.now()
        notification.save(update_fields=["read_at"])

    return redirect("community_notifications")


@community_required
@require_POST
def notification_mark_all_read(request):
    """Marquer comme lues toutes les notifications du compte connecté."""
    Notification.objects.filter(
        recipient=request.user,
        read_at__isnull=True,
    ).update(read_at=timezone.now())

    messages.success(request, "Vos notifications ont été marquées comme lues.")
    return redirect("community_notifications")
