"""Security middleware: response headers (incl. a Content-Security-Policy) and rate limiting.

No extra packages needed. Counters live in Django's cache, which is per-process by default;
set REDIS_URL in production so every server process shares them (see settings/base.py).
"""
import secrets
import time

from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse
from django.contrib.auth.signals import user_logged_in, user_login_failed
from django.dispatch import receiver

# --- Content Security Policy ------------------------------------------------
# Only our own scripts run (inline ones need the per-request nonce). Video embeds are limited
# to the two players apps/media_library/embeds.py can produce.
_FRAMES = "https://www.youtube-nocookie.com https://player.vimeo.com"


def _csp(nonce: str) -> str:
    parts = {
        "default-src": "'self'",
        "script-src": f"'self' 'nonce-{nonce}'",
        "style-src": "'self' 'unsafe-inline'",
        "img-src": "'self' data: blob: https:",
        "media-src": "'self' blob: https:",
        "font-src": "'self'",
        "connect-src": "'self' ws: wss:",
        "frame-src": _FRAMES,
        "object-src": "'none'",
        "base-uri": "'self'",
        "form-action": "'self'",
        "frame-ancestors": "'none'",
    }
    if not settings.DEBUG:
        parts["upgrade-insecure-requests"] = ""
    return "; ".join(f"{k} {v}".strip() for k, v in parts.items())


class SecurityHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.csp_nonce = secrets.token_urlsafe(16)
        response = self.get_response(request)
        # The Django admin ships its own inline scripts; it is staff-only and still gets the other headers.
        if not request.path.startswith("/admin/"):
            response.setdefault("Content-Security-Policy", _csp(request.csp_nonce))
        response.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=(), payment=(self), usb=()")
        response.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        response.setdefault("X-Content-Type-Options", "nosniff")
        # Pages with accounts or money on them must never be stored by shared caches.
        if request.user.is_authenticated if hasattr(request, "user") else False:
            response.setdefault("Cache-Control", "private, no-cache")
        return response


# --- Rate limiting ---------------------------------------------------------
def client_ip(request) -> str:
    if settings.TRUST_PROXY_HEADERS:
        fwd = request.META.get("HTTP_X_FORWARDED_FOR", "")
        if fwd:
            return fwd.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "unknown")


def _hit(key: str, window: int) -> int:
    """Count one request in a fixed window and return how many have happened in it."""
    now = int(time.time())
    bucket = f"rl:{key}:{now // window}"
    if cache.add(bucket, 1, window + 1):
        return 1
    try:
        return cache.incr(bucket)
    except ValueError:  # expired between add() and incr()
        cache.set(bucket, 1, window + 1)
        return 1


_SENSITIVE_PREFIXES = ("/accounts/login", "/accounts/signup", "/api/auth", "/give/", "/api/giving", "/books/checkout")


def _too_many(retry_after: int) -> HttpResponse:
    resp = HttpResponse(
        "Too many requests. Please wait a moment and try again.",
        status=429,
        content_type="text/plain; charset=utf-8",
    )
    resp["Retry-After"] = str(retry_after)
    return resp


class RateLimitMiddleware:
    """Per-IP limits: a generous one for everything, a strict one for login/sign-up/giving writes,
    and a temporary block after repeated failed sign-ins."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        if path.startswith(("/static/", "/media/")) or path in ("/service-worker.js", "/manifest.webmanifest"):
            return self.get_response(request)
        ip = client_ip(request)

        if request.method in ("POST", "PUT", "PATCH", "DELETE") and path.startswith(_SENSITIVE_PREFIXES):
            if cache.get(f"lockout:{ip}"):
                return _too_many(settings.LOGIN_LOCKOUT_SECONDS)
            if _hit(f"sens:{ip}", 60) > settings.RATE_LIMIT_SENSITIVE_PER_MIN:
                return _too_many(60)
        if _hit(f"all:{ip}", 60) > settings.RATE_LIMIT_PER_MIN:
            return _too_many(60)
        return self.get_response(request)


@receiver(user_login_failed)
def _count_failure(sender, credentials, request=None, **kwargs):
    if request is None:
        return
    ip = client_ip(request)
    key = f"loginfail:{ip}"
    cache.add(key, 0, settings.LOGIN_LOCKOUT_SECONDS)
    try:
        n = cache.incr(key)
    except ValueError:
        n = 1
        cache.set(key, 1, settings.LOGIN_LOCKOUT_SECONDS)
    if n >= settings.LOGIN_MAX_FAILURES:
        cache.set(f"lockout:{ip}", 1, settings.LOGIN_LOCKOUT_SECONDS)


@receiver(user_logged_in)
def _clear_failures(sender, request=None, **kwargs):
    if request is not None:
        cache.delete(f"loginfail:{client_ip(request)}")
