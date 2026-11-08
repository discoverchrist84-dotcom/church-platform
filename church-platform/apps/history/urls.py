from django.urls import path

from . import views

app_name = "history"

urlpatterns = [
    path("", views.timeline, name="timeline"),
    path("search/", views.search_page, name="search"),
    path("events/<slug:slug>/", views.event_detail, name="event"),
    path("figures/<slug:slug>/", views.figure_detail, name="figure"),
]
