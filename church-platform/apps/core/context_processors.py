from django.conf import settings

from .site_info import site_info


def site(request):
    unread = 0
    user = getattr(request, "user", None)
    if user is not None and user.is_authenticated:
        unread = user.notifications.filter(is_read=False).count()
    return {
        **site_info(),  # name, logo, banner, contact: editable in the admin under "Website settings"
        "SITE_LOGO": settings.SITE_LOGO,  # kept for older templates
        "THEME_COLOR": settings.THEME_COLOR,
        "DEFAULT_CURRENCY": settings.DEFAULT_CURRENCY,
        "unread_notifications": unread,
        "cart_count": sum((request.session.get("book_cart") or {}).values()) if hasattr(request, "session") else 0,
        "csp_nonce": getattr(request, "csp_nonce", ""),
    }
