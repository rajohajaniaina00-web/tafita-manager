from django.contrib import admin
from .models import (
    CommunityPost, Conversation, ConversationMessage, ConversationParticipant,
    EventComment, EventReaction, MemberInvitation, MemberPaymentSubmission, PostComment, PostReaction,
)


@admin.register(MemberInvitation)
class MemberInvitationAdmin(admin.ModelAdmin):
    list_display = ("member", "created_at", "expires_at", "used_at", "created_by")
    search_fields = ("member__first_name", "member__last_name", "member__email")
    readonly_fields = ("created_at", "used_at")


@admin.register(CommunityPost)
class CommunityPostAdmin(admin.ModelAdmin):
    list_display = ("id", "author", "status", "created_at", "moderated_by")
    list_filter = ("status", "created_at")
    search_fields = ("author__username", "content")
    readonly_fields = ("created_at", "updated_at", "moderated_at")


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "kind", "last_activity")
    list_filter = ("kind",)
    search_fields = ("title",)

admin.site.register(PostComment)
admin.site.register(PostReaction)
admin.site.register(EventComment)
admin.site.register(EventReaction)
admin.site.register(ConversationParticipant)
admin.site.register(ConversationMessage)


@admin.register(MemberPaymentSubmission)
class MemberPaymentSubmissionAdmin(admin.ModelAdmin):
    list_display = ("id", "contribution", "submitted_by", "amount", "method", "status", "created_at")
    list_filter = ("status", "method", "created_at")
    search_fields = ("submitted_by__username", "contribution__title", "reference")
    readonly_fields = ("created_at", "reviewed_at")
