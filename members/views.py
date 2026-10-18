
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import MemberForm
from .models import Member


@login_required
@permission_required("members.view_member", raise_exception=True)
def member_list(request):
    query = request.GET.get("q", "").strip()
    members = Member.objects.all()

    if query:
        members = (
            members.filter(first_name__icontains=query)
            | members.filter(last_name__icontains=query)
            | members.filter(email__icontains=query)
            | members.filter(phone__icontains=query)
        )

    return render(
        request,
        "members/list.html",
        {"members": members, "query": query},
    )


@login_required
@permission_required("members.add_member", raise_exception=True)
def member_create(request):
    form = MemberForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Le membre a été ajouté.")
        return redirect("member_list")

    return render(
        request,
        "members/form.html",
        {"form": form, "page_title": "Ajouter un membre"},
    )


@login_required
@permission_required("members.change_member", raise_exception=True)
def member_update(request, pk):
    member = get_object_or_404(Member, pk=pk)
    form = MemberForm(request.POST or None, instance=member)

    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Le membre a été modifié.")
        return redirect("member_list")

    return render(
        request,
        "members/form.html",
        {"form": form, "page_title": "Modifier un membre"},
    )


@login_required
@permission_required("members.delete_member", raise_exception=True)
@require_POST
def member_delete(request, pk):
    member = get_object_or_404(Member, pk=pk)
    member.delete()
    messages.success(request, "Le membre a été supprimé.")
    return redirect("member_list")
