from datetime import datetime

from django.shortcuts import get_object_or_404
from ninja import Router, Schema
from ninja.errors import HttpError
from ninja.security import django_auth

from .models import Conversation, Message, Notification

router = Router(auth=django_auth)


class ConversationOut(Schema):
    id: int
    kind: str
    name: str


class MessageOut(Schema):
    id: int
    sender: str
    body: str
    created_at: datetime

    @staticmethod
    def resolve_sender(obj):
        return obj.sender.get_username()


class NotificationOut(Schema):
    id: int
    title: str
    body: str
    url: str
    is_read: bool
    created_at: datetime


@router.get("/conversations", response=list[ConversationOut])
def my_conversations(request):
    return Conversation.objects.filter(participants=request.user)


@router.get("/conversations/{conversation_id}/messages", response=list[MessageOut])
def history(request, conversation_id: int, before_id: int | None = None, limit: int = 50):
    conv = get_object_or_404(Conversation, pk=conversation_id)
    if not conv.has_participant(request.user):
        raise HttpError(403, "Not a participant.")
    qs = Message.objects.filter(conversation=conv).select_related("sender")
    if before_id:
        qs = qs.filter(pk__lt=before_id)
    limit = max(1, min(limit, 100))
    return list(reversed(list(qs.order_by("-created_at")[:limit])))


@router.get("/notifications", response=list[NotificationOut])
def notifications(request, unread_only: bool = False):
    qs = Notification.objects.filter(user=request.user)
    if unread_only:
        qs = qs.filter(is_read=False)
    return qs[:50]


@router.post("/notifications/{note_id}/read")
def mark_read(request, note_id: int):
    note = get_object_or_404(Notification, pk=note_id, user=request.user)
    note.is_read = True
    note.save(update_fields=["is_read", "updated_at"])
    return {"ok": True}
