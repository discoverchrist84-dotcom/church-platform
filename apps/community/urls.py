"""Mounted under /branches/<slug>/ (see config/urls.py), so every view receives `slug`."""
from django.urls import path

from . import views

app_name = "community"

urlpatterns = [
    path("events/", views.events, name="events"),
    path("events/new/", views.event_create, name="event_create"),
    path("events/<int:event_id>/rsvp/", views.event_rsvp, name="event_rsvp"),
    path("announcements/new/", views.announcement_create, name="announcement_create"),
    path("board/", views.board, name="board"),
    path("board/new/", views.post_create, name="post_create"),
    path("board/<int:post_id>/", views.post_detail, name="post_detail"),
    path("groups/", views.groups, name="groups"),
    path("groups/<slug:ministry_slug>/join/", views.group_join, name="group_join"),
    path("groups/<slug:ministry_slug>/leave/", views.group_leave, name="group_leave"),
    path("prayer/", views.prayer, name="prayer"),
    path("prayer/<int:pk>/answered/", views.prayer_answered, name="prayer_answered"),
    path("moderation/", views.moderation, name="moderation"),
    path("moderation/<int:report_id>/<str:action>/", views.resolve_report, name="resolve_report"),
    path("moderate/<str:kind>/<int:pk>/toggle/", views.toggle_hidden, name="toggle_hidden"),
    path("report/<str:kind>/<int:pk>/", views.report, name="report"),
]
