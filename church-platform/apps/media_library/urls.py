"""Mounted under /branches/<slug>/ (see config/urls.py)."""
from django.urls import path

from . import views

app_name = "media_library"

urlpatterns = [
    path("sermons/", views.sermons, name="sermons"),
    path("sermons/new/", views.sermon_create, name="sermon_create"),
]
