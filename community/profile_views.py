from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from members.models import Member
from .profile_forms import MemberPhotoForm


def _has_admin_profile_access(user):
    if not user.is_authenticated or not user.is_active:
        return False

    return bool(
        user.is_staff
        or user.is_superuser
        or user.has_perm("members.view_member")
        or user.has_perm("members.change_member")
        or user.has_perm("events.view_event")
        or user.has_perm("events.add_event")
        or user.has_perm("contributions.view_contribution")
        or user.has_perm("contributions.add_contribution")
    )


@login_required
@require_http_methods(["GET", "POST"])
def member_profile(request):
    """Permet à un membre de gérer uniquement la photo de sa propre fiche."""
    member = Member.objects.filter(user=request.user).first()

    # Un compte administratif n'a pas nécessairement de fiche membre.
    if member is None and _has_admin_profile_access(request.user):
        return render(
            request,
            "community/profile_admin.html",
            {"profile_user": request.user},
        )

    if member is None:
        return render(
            request,
            "community/profile_not_linked.html",
            status=403,
        )

    if member.status != "active":
        return render(
            request,
            "community/profile_not_linked.html",
            {"inactive": True},
            status=403,
        )

    form = MemberPhotoForm()
    if request.method == "POST":
        if request.POST.get("remove_photo") == "1":
            if member.photo:
                old_name = member.photo.name
                storage = member.photo.storage
                member.photo = ""
                member.save(update_fields=["photo"])
                if old_name:
                    storage.delete(old_name)
            messages.success(request, "Votre photo de profil a été supprimée.")
            return redirect("community_member_profile")

        form = MemberPhotoForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_photo = form.cleaned_data.get("photo")
            if uploaded_photo is None:
                form.add_error("photo", "Choisissez une image avant de continuer.")
            else:
                old_name = member.photo.name if member.photo else ""
                member.photo = uploaded_photo
                member.save(update_fields=["photo"])
                if old_name and old_name != member.photo.name:
                    member.photo.storage.delete(old_name)
                messages.success(request, "Votre photo de profil a été mise à jour.")
                return redirect("community_member_profile")

    return render(
        request,
        "community/profile.html",
        {"member": member, "form": form},
    )
