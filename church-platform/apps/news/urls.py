from django.urls import path

from . import views

app_name = "news"

urlpatterns = [
    path("", views.news_list, name="list"),
    path("announcements/", views.bulletin_list, name="bulletins"),
    path("announcements/<int:pk>/", views.bulletin_detail, name="bulletin"),
    path("feed/", views.NewsFeed(), name="feed"),
    path("<slug:slug>/", views.news_detail, name="detail"),
]
