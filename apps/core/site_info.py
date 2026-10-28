"""One place that answers "what is the site called and what does its logo look like?".

Combines the editable SiteSettings row with the defaults in settings.py. Results are cached
briefly so the header does not hit the database on every request.
"""
from django.conf import settings
from django.core.cache import cache
from django.db import DatabaseError
from django.templatetags.static import static

from .models import SiteSettings

CACHE_SECONDS = 60


def site_info() -> dict:
    cached = cache.get(SiteSettings.CACHE_KEY)
    if cached is not None:
        return cached
    try:
        s = SiteSettings.objects.filter(pk=1).first()
    except DatabaseError:  # before the first migrate
        s = None
    g = lambda attr, default: (getattr(s, attr, "") or default) if s else default  # noqa: E731
    logo_url = static(settings.SITE_LOGO)
    if s and s.logo:
        try:
            if s.logo.storage.exists(s.logo.name):
                logo_url = s.logo.url
        except Exception:
            pass
    info = {
        "SITE_NAME": g("church_name", settings.SITE_NAME),
        "SITE_BRAND": g("brand", settings.SITE_BRAND),
        "SITE_SUBBRAND": g("sub_brand", settings.SITE_SUBBRAND),
        "SITE_SHORT_NAME": g("short_name", settings.SITE_SHORT_NAME),
        "SITE_DESCRIPTION": g("tagline", settings.SITE_DESCRIPTION),
        "SITE_LOGO_URL": logo_url,
        "WELCOME_TEXT": g("welcome_text", ""),
        "BANNER": {"text": s.banner_text, "link": s.banner_link} if s and s.banner_is_active and s.banner_text else None,
        "CONTACT": {
            "email": g("contact_email", ""), "phone": g("contact_phone", ""), "address": g("address", ""),
            "footer_note": g("footer_note", ""),
            "social": [(label, url) for label, url in (
                ("Facebook", g("facebook_url", "")), ("YouTube", g("youtube_url", "")),
                ("Instagram", g("instagram_url", "")), ("X", g("x_url", "")), ("WhatsApp", g("whatsapp_url", "")),
            ) if url],
        },
    }
    cache.set(SiteSettings.CACHE_KEY, info, CACHE_SECONDS)
    return info
