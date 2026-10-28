from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from .models import Conversation, Message


class ChatConsumer(AsyncJsonWebsocketConsumer):
    """ws://host/ws/chat/<conversation_id>/ — authenticated, participants only."""

    async def connect(self):
        self.user = self.scope["user"]
        self.conversation_id = int(self.scope["url_route"]["kwargs"]["conversation_id"])
        self.group = f"chat_{self.conversation_id}"

        if not await self._allowed():
            await self.close(code=4403)
            return
        await self.channel_layer.group_add(self.group, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        if hasattr(self, "group"):
            await self.channel_layer.group_discard(self.group, self.channel_name)

    async def receive_json(self, content, **kwargs):
        body = str(content.get("message", "")).strip()[:2000]
        if not body:
            return
        msg = await self._save(body)
        await self.channel_layer.group_send(
            self.group,
            {
                "type": "chat.message",
                "id": msg["id"],
                "sender": msg["sender"],
                "message": body,
                "created_at": msg["created_at"],
            },
        )

    async def chat_message(self, event):
        await self.send_json({k: v for k, v in event.items() if k != "type"})

    @database_sync_to_async
    def _allowed(self):
        try:
            conv = Conversation.objects.get(pk=self.conversation_id)
        except Conversation.DoesNotExist:
            return False
        return conv.has_participant(self.user)

    @database_sync_to_async
    def _save(self, body):
        m = Message.objects.create(conversation_id=self.conversation_id, sender=self.user, body=body)
        return {"id": m.pk, "sender": self.user.get_username(), "created_at": m.created_at.isoformat()}


class NotificationConsumer(AsyncJsonWebsocketConsumer):
    """ws://host/ws/notifications/ — pushes new notifications to the signed-in user."""

    async def connect(self):
        self.user = self.scope["user"]
        if not self.user.is_authenticated:
            await self.close(code=4401)
            return
        self.group = f"user_{self.user.pk}"
        await self.channel_layer.group_add(self.group, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        if hasattr(self, "group"):
            await self.channel_layer.group_discard(self.group, self.channel_name)

    async def notify(self, event):
        await self.send_json({k: v for k, v in event.items() if k != "type"})
