
from django.urls import path
from . import views

urlpatterns = [
    path("", views.member_list, name="member_list"),
    path("ajouter/", views.member_create, name="member_create"),
    path("<int:pk>/modifier/", views.member_update, name="member_update"),
    path("<int:pk>/supprimer/", views.member_delete, name="member_delete"),
]
