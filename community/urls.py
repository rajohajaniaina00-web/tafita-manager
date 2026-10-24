from django.urls import path
from . import views, profile_views


urlpatterns = [
    path("notifications/", views.notification_list, name="community_notifications"),
    path("notifications/marquer-tout-lu/", views.notification_mark_all_read, name="community_notifications_mark_all_read"),
    path("notifications/<int:notification_id>/lire/", views.notification_mark_read, name="community_notification_mark_read"),
    path("connexion/", views.member_login_view, name="member_login"),
    path("inscription/", views.member_register_view, name="member_register"),
    path("deconnexion/", views.member_logout_view, name="member_logout"),
    path("", views.community_feed, name="community_feed"),
    path("profil/", profile_views.member_profile, name="community_member_profile"),
    path("publication/creer/", views.create_post, name="community_create_post"),
    path("publication/<int:post_id>/j-adore/", views.toggle_post_love, name="community_post_love"),
    path("publication/<int:post_id>/commenter/", views.add_post_comment, name="community_post_comment"),
    path("evenement/<int:event_id>/", views.event_detail, name="community_event_detail"),
    path("evenement/<int:event_id>/j-adore/", views.toggle_event_love, name="community_event_love"),
    path("evenement/<int:event_id>/commenter/", views.add_event_comment, name="community_event_comment"),
    path("administration/codes-membre/", views.activation_codes, name="community_activation_codes"),
    path("administration/comptes/<int:member_id>/supprimer/", views.delete_member_account, name="community_delete_member_account"),
    path("administration/publications/", views.post_moderation, name="community_post_moderation"),
    path("administration/publications/<int:post_id>/<str:action>/", views.moderate_post, name="community_moderate_post"),
    path("cotisations/", views.my_contributions, name="community_my_contributions"),
    path("cotisations/<int:contribution_id>/declarer-paiement/", views.submit_member_payment, name="community_submit_payment"),
    path("administration/paiements/", views.payment_submission_moderation, name="community_payment_moderation"),
    path("administration/paiements/<int:submission_id>/<str:action>/", views.review_member_payment, name="community_review_payment"),
    path("discussions/", views.discussions, name="community_discussions"),
    path("discussions/groupes/creer/", views.create_group_conversation, name="community_create_group"),
    path("discussions/privees/<int:user_id>/", views.start_direct_conversation, name="community_start_direct"),
    path("discussions/<int:conversation_id>/", views.conversation_detail, name="community_conversation"),
    path("discussions/<int:conversation_id>/messages/", views.conversation_messages_json, name="community_messages_json"),
]
