
from django.contrib import admin
from .models import Event


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "date",
        "location",
        "responsible",
        "status",
    )

    list_filter = ("status", "date")

    search_fields = (
        "title",
        "location",
        "responsible",
    )

    ordering = ("date",)

    date_hierarchy = "date"
