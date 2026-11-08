from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from .api import api

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", api.urls),
    path("accounts/", include("apps.accounts.urls")),
    path("history/", include("apps.history.urls")),
    path("branches/<slug:slug>/", include("apps.community.urls")),
    path("branches/<slug:slug>/", include("apps.media_library.urls")),
    path("branches/", include("apps.churches.urls")),
    path("leadership/", include("apps.leadership.urls")),
    path("give/", include("apps.giving.urls")),
    path("books/", include("apps.bookstore.urls")),
    path("news/", include("apps.news.urls")),
    path("notifications/", include("apps.realtime.urls")),
    path("", include("apps.core.urls")),
]

if settings.DEBUG or settings.SERVE_MEDIA:
    from django.urls import re_path
    from django.views.static import serve as _serve

    _prefix = settings.MEDIA_URL.strip("/")
    if settings.MEDIA_STORAGE == "database" and "S3Storage" not in settings.STORAGES["default"]["BACKEND"]:
        from apps.core.views import media_from_database

        urlpatterns += [re_path(rf"^{_prefix}/(?P<path>.*)$", media_from_database)]
    else:
        urlpatterns += [re_path(rf"^{_prefix}/(?P<path>.*)$", _serve, {"document_root": settings.MEDIA_ROOT})]
