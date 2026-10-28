from django.urls import path

from . import views

app_name = "news"

urlpatterns = [
    path("", views.news_list, name="list"),
    path("feed/", views.NewsFeed(), name="feed"),
    path("<slug:slug>/", views.news_detail, name="detail"),
]
