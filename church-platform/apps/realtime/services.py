from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .models import Notification


def notify(user, title: str, body: str = "", url: str = "") -> Notification:
    """Store a notification and push it live to any open sessions of `user`.

    Call from sync code (views, API handlers, Celery tasks).
    """
    note = Notification.objects.create(user=user, title=title, body=body, url=url)
    layer = get_channel_layer()
    if layer is not None:
        async_to_sync(layer.group_send)(
            f"user_{user.pk}",
            {"type": "notify", "id": note.pk, "title": title, "body": body, "url": url},
        )
    return note


def notify_many(users, title: str, body: str = "", url: str = "") -> int:
    """Store one notification per user and push each live. Returns how many were created."""
    users = list(users)
    if not users:
        return 0
    Notification.objects.bulk_create(
        [Notification(user=u, title=title, body=body, url=url) for u in users]
    )
    layer = get_channel_layer()
    if layer is not None:
        send = async_to_sync(layer.group_send)
        for u in users:
            try:
                send(f"user_{u.pk}", {"type": "notify", "title": title, "body": body, "url": url})
            except Exception:  # a dead layer must not lose the stored notifications
                break
    return len(users)
