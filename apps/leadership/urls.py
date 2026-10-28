from django.urls import path

from . import views

app_name = "leadership"

urlpatterns = [
    path("", views.council_list, name="list"),
    path("<slug:slug>/", views.council_detail, name="council"),
    path("<slug:slug>/<int:pk>/", views.member_detail, name="member"),
]
