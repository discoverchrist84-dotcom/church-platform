from django.urls import path

from django.contrib.sitemaps.views import sitemap

from . import views
from .seo import SITEMAPS, robots_txt

app_name = "core"

urlpatterns = [
    path("", views.home, name="home"),
    path("robots.txt", robots_txt, name="robots"),
    path("sitemap.xml", sitemap, {"sitemaps": SITEMAPS}, name="sitemap"),
    path("offline/", views.offline, name="offline"),
    path("manifest.webmanifest", views.manifest, name="manifest"),
    path("service-worker.js", views.service_worker, name="service_worker"),
]
