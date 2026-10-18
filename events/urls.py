
from django.urls import path
from . import views

urlpatterns = [
    path("", views.events_list, name="events_list"),
    path("ajouter/", views.event_create, name="event_create"),
    path("<int:pk>/modifier/", views.event_update, name="event_update"),
    path("<int:pk>/supprimer/", views.event_delete, name="event_delete"),
]
