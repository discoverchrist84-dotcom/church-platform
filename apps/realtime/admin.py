from django.contrib import admin

from apps.core.admin_base import FriendlyAdmin

from .models import Conversation, Message, Notification, PushSubscription


@admin.register(Conversation)
class ConversationAdmin(FriendlyAdmin):
    help_list = "Chat conversations. Members create these themselves; you rarely need to change them."
    list_display = ("__str__", "kind", "branch", "created_at")
    list_filter = ("kind", "branch__level")
    filter_horizontal = ("participants",)


@admin.register(Message)
class MessageAdmin(FriendlyAdmin):
    help_list = "Chat messages. Delete one only if it breaks the church's rules."
    list_display = ("conversation", "sender", "created_at")
    search_fields = ("body", "sender__username")


@admin.register(Notification)
class NotificationAdmin(FriendlyAdmin):
    help_list = "Alerts shown to members. Read ones can be deleted to tidy up."
    list_display = ("user", "title", "is_read", "created_at")
    list_filter = ("is_read",)
    search_fields = ("title", "user__username")


@admin.register(PushSubscription)
class PushSubscriptionAdmin(FriendlyAdmin):
    help_list = "Devices that have agreed to receive push alerts."
