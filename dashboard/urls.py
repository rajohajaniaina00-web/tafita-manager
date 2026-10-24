
from django.urls import path
from . import views

urlpatterns = [
    path("", views.dashboard_view, name="dashboard"),
    path(
        "espace-membre/",
        views.member_home,
        name="member_home",
    ),
]
