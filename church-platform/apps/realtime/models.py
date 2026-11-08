from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel


class Conversation(TimeStampedModel):
    class Kind(models.TextChoices):
        BRANCH = "branch", "Branch room"
        GROUP = "group", "Group chat"
        DIRECT = "direct", "Direct message"

    kind = models.CharField(max_length=10, choices=Kind.choices, default=Kind.GROUP)
    name = models.CharField(max_length=160, blank=True)
    branch = models.ForeignKey(
        "churches.Branch", null=True, blank=True, on_delete=models.CASCADE, related_name="conversations"
    )
    participants = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name="conversations")

    def __str__(self):
        return self.name or f"{self.get_kind_display()} #{self.pk}"

    def has_participant(self, user) -> bool:
        if not user.is_authenticated:
            return False
        if self.kind == self.Kind.BRANCH and self.branch_id:
            # anyone who belongs to the branch may join its room
            return user.memberships.filter(branch_id=self.branch_id).exists()
        return self.participants.filter(pk=user.pk).exists()


class Message(TimeStampedModel):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="messages")
    body = models.TextField(max_length=2000)

    class Meta:
        ordering = ["created_at"]
        indexes = [models.Index(fields=["conversation", "created_at"])]


class Notification(TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    title = models.CharField(max_length=200)
    body = models.TextField(blank=True)
    url = models.CharField(max_length=255, blank=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]


class PushSubscription(TimeStampedModel):
    """Web Push endpoint for a user's browser/device (used once push is wired up)."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="push_subscriptions")
    endpoint = models.TextField(unique=True)
    p256dh = models.CharField(max_length=255)
    auth = models.CharField(max_length=255)
