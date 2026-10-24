from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods, require_POST


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


@require_http_methods(["GET", "POST"])
def login_view(request):
    """Connexion de l’administration. Les membres utilisent /communaute/connexion/."""
    if request.user.is_authenticated:
        if has_admin_access(request.user):
            return redirect("dashboard")
        return redirect("community_feed")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        user = authenticate(request, username=username, password=password)

        if user is None:
            messages.error(request, "Nom d’utilisateur ou mot de passe incorrect.")
        elif not (has_admin_access(user) or user.is_staff):
            messages.error(
                request,
                "Cette page est réservée à l’administration. Utilisez la connexion membre.",
            )
        else:
            login(request, user)
            messages.success(request, "Connexion réussie.")
            if has_admin_access(user):
                return redirect("dashboard")
            return redirect("community_feed")

    return render(request, "accounts/login.html")


@login_required
@require_POST
def logout_view(request):
    logout(request)
    messages.success(request, "Vous avez été déconnecté.")
    return redirect("login")
