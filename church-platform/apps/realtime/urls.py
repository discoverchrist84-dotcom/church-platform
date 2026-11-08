from django.urls import path

from . import views

app_name = "realtime"

urlpatterns = [
    path("", views.notifications, name="list"),
    path("read-all/", views.read_all, name="read_all"),
    path("<int:pk>/open/", views.open_notification, name="open"),
]
