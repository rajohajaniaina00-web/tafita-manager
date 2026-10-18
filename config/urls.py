
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("members/", include("members.urls")),
    path("events/", include("events.urls")),
    path("", include("dashboard.urls")),
    path("contributions/", include("contributions.urls")),
]
