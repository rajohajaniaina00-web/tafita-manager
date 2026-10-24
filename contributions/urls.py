from django.urls import path
from . import views

urlpatterns = [
    path("", views.contribution_list, name="contribution_list"),
    path(
        "ajouter/",
        views.contribution_create,
        name="contribution_create",
    ),
    path(
        "<int:pk>/paiement/",
        views.payment_create,
        name="payment_create",
    ),
    path(
        "paiement/<int:pk>/supprimer/",
        views.payment_delete,
        name="payment_delete",
    ),

]
