from .base import *  # noqa: F401,F403
from .base import env

DEBUG = False

# Behind Nginx / a load balancer terminating TLS.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 60 * 60 * 24 * 365  # tell browsers to use HTTPS only, for a year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = env.bool("SECURE_HSTS_PRELOAD", default=False)
TRUST_PROXY_HEADERS = env.bool("TRUST_PROXY_HEADERS", default=True)
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])

# --- Railway (and similar hosts) ------------------------------------------------
# Signing in is a POST, and Django refuses it (403 "CSRF verification failed") unless the site's own
# https address is trusted. Railway tells us its address, so trust it automatically.
_domains = [d for d in (env("RAILWAY_PUBLIC_DOMAIN", default=""), env("RAILWAY_STATIC_URL", default="")) if d]
for _d in _domains:
    _d = _d.replace("https://", "").replace("http://", "").strip("/")
    if _d not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(_d)
    if f"https://{_d}" not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(f"https://{_d}")
if env.bool("TRUST_RAILWAY_DOMAINS", default=bool(_domains)):
    ALLOWED_HOSTS.append(".up.railway.app")
    CSRF_TRUSTED_ORIGINS.append("https://*.up.railway.app")
# Your own domain: set ALLOWED_HOSTS=yourchurch.org,www.yourchurch.org and CSRF_TRUSTED_ORIGINS=https://yourchurch.org,https://www.yourchurch.org

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = env("EMAIL_HOST", default="localhost")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = True
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="no-reply@example.org")

if env("SECRET_KEY", default="dev-insecure-change-me") == "dev-insecure-change-me":
    raise RuntimeError("Set a real SECRET_KEY in production.")
