from celery import shared_task
from django.contrib.auth import get_user_model

from .services import notify_many


@shared_task
def notify_users(user_ids, title, body="", url=""):
    """Fan a notification out to many users (runs inline when no Celery broker is configured)."""
    users = get_user_model().objects.filter(pk__in=list(user_ids), is_active=True)
    return notify_many(users, title, body, url)
