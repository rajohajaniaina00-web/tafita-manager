from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("communaute/", include("community.urls")),
    path("members/", include("members.urls")),
    path("events/", include("events.urls")),
    path("contributions/", include("contributions.urls")),
    path("", include("dashboard.urls")),
    path("assistant-ia/", include("ai_assistant.urls")),
]

if settings.DEBUG:
    urlpatterns += static(
        getattr(settings, "MEDIA_URL", "/media/"),
        document_root=getattr(settings, "MEDIA_ROOT", str(settings.BASE_DIR) + "/media"),
    )
