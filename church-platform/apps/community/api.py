from datetime import datetime

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import Router, Schema
from ninja.errors import HttpError
from ninja.security import django_auth

from apps.churches.models import Branch
from apps.core.permissions import can_manage_branch

from .models import Announcement, Event, EventRSVP

router = Router()


class AnnouncementOut(Schema):
    id: int
    title: str
    body: str
    is_pinned: bool
    created_at: datetime


class AnnouncementIn(Schema):
    title: str
    body: str
    is_pinned: bool = False


class EventOut(Schema):
    id: int
    title: str
    description: str
    location: str
    starts_at: datetime
    ends_at: datetime | None = None
    capacity: int | None = None
    going_count: int = 0

    @staticmethod
    def resolve_going_count(obj):
        return obj.rsvps.filter(status=EventRSVP.Status.GOING).count()


class RSVPIn(Schema):
    status: str = EventRSVP.Status.GOING


@router.get("/branches/{slug}/announcements", response=list[AnnouncementOut])
def list_announcements(request, slug: str):
    branch = get_object_or_404(Branch, slug=slug, is_active=True)
    return Announcement.objects.filter(branch=branch, is_published=True)[:50]


@router.post("/branches/{slug}/announcements", response={201: AnnouncementOut}, auth=django_auth)
def create_announcement(request, slug: str, payload: AnnouncementIn):
    branch = get_object_or_404(Branch, slug=slug, is_active=True)
    if not can_manage_branch(request.user, branch):
        raise HttpError(403, "Only branch leaders can post announcements.")
    obj = Announcement.objects.create(branch=branch, author=request.user, **payload.dict())
    return 201, obj


@router.get("/branches/{slug}/events", response=list[EventOut])
def list_events(request, slug: str, upcoming: bool = True):
    branch = get_object_or_404(Branch, slug=slug, is_active=True)
    qs = Event.objects.filter(branch=branch)
    if upcoming:
        qs = qs.filter(starts_at__gte=timezone.now())
    return qs[:50]


@router.post("/events/{event_id}/rsvp", auth=django_auth)
def rsvp(request, event_id: int, payload: RSVPIn):
    if payload.status not in EventRSVP.Status.values:
        raise HttpError(400, "Invalid status.")
    with transaction.atomic():
        event = get_object_or_404(Event.objects.select_for_update(), pk=event_id)
        if payload.status == EventRSVP.Status.GOING and event.capacity is not None:
            going = event.rsvps.filter(status=EventRSVP.Status.GOING).exclude(user=request.user).count()
            if going >= event.capacity:
                raise HttpError(409, "This event is full.")
        EventRSVP.objects.update_or_create(
            event=event, user=request.user, defaults={"status": payload.status}
        )
    return {"status": payload.status}
