from django.contrib import admin
from .models import Member


@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = (
        "first_name",
        "last_name",
        "email",
        "phone",
        "joined_on",
        "status",
    )
    list_filter = ("status", "joined_on")
    search_fields = ("first_name", "last_name", "email", "phone")
    list_per_page = 20