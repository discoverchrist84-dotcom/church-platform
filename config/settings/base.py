from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY", default="dev-insecure-change-me")
DEBUG = env.bool("DEBUG", default=False)
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

# --- Database -------------------------------------------------------------
# Postgres in docker/prod (DATABASE_URL), SQLite fallback for a quick start.
DATABASES = {
    "default": env.db("DATABASE_URL", default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}")
}
USING_POSTGRES = "postgresql" in DATABASES["default"]["ENGINE"]

# --- Apps -----------------------------------------------------------------
INSTALLED_APPS = [
    "daphne",  # must come first so `runserver` serves ASGI (websockets)
    "apps.core.admin_config.ChurchAdminConfig",  # Django admin, with our friendly dashboard
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "channels",
    # Local apps
    "apps.core",
    "apps.accounts",
    "apps.churches",
    "apps.leadership",
    "apps.history",
    "apps.community",
    "apps.media_library",
    "apps.giving",
    "apps.bookstore",
    "apps.news",
    "apps.realtime",
]
if USING_POSTGRES:
    INSTALLED_APPS.insert(INSTALLED_APPS.index("channels"), "django.contrib.postgres")

AUTH_USER_MODEL = "accounts.User"

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "apps.core.security.RateLimitMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.core.security.SecurityHeadersMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.core.context_processors.site",
            ],
            "builtins": ["apps.core.templatetags.media_tags"],
        },
    },
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "core:home"
LOGOUT_REDIRECT_URL = "core:home"

# --- i18n -----------------------------------------------------------------
LANGUAGE_CODE = "en"
TIME_ZONE = env("TIME_ZONE", default="UTC")  # e.g. Africa/Lagos, America/Los_Angeles
USE_I18N = True
USE_TZ = True

# --- Site branding (edit these) ------------------------------------------
SITE_NAME = env(
    "SITE_NAME",
    default="Christ Ascension Church 1984 Foundation Constitution (Lifters Power Assembly)",
)
SITE_BRAND = env("SITE_BRAND", default="Christ Ascension Church")  # header, line 1
SITE_SUBBRAND = env("SITE_SUBBRAND", default="Lifters Power Assembly")  # header, line 2
SITE_SHORT_NAME = env("SITE_SHORT_NAME", default="Lifters Power")  # home-screen label
SITE_LOGO = env("SITE_LOGO", default="img/logo.png")  # path under /static/
SITE_DESCRIPTION = (
    "Christ Ascension Church (Lifters Power Assembly): explore the history of the church, "
    "find your branch, hear sermons and stay connected."
)
THEME_COLOR = "#0b2a5b"  # navy
BACKGROUND_COLOR = "#071a38"  # splash-screen background when the installed app opens

# --- Static & media -------------------------------------------------------
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
# Uploaded pictures and files. Django serves them itself unless you set SERVE_MEDIA=False
# (do that once a web server or object storage such as S3 serves /media/ for you).
SERVE_MEDIA = env.bool("SERVE_MEDIA", default=True)
MAX_IMAGE_MB = env.int("MAX_IMAGE_MB", default=25)  # pictures are shrunk automatically after upload
MEDIA_URL = "/media/"
MEDIA_ROOT = env.path("MEDIA_ROOT", default=str(BASE_DIR / "media"))  # on Railway: a volume, e.g. /data/media
# Paid e-books are kept here, NOT under /media/, so they can only be downloaded by people who bought them.
PRIVATE_MEDIA_ROOT = env.path("PRIVATE_MEDIA_ROOT", default=str(BASE_DIR / "private_media"))
BOOKSTORE_SHIPPING_FEE = env("BOOKSTORE_SHIPPING_FEE", default="0")  # flat delivery fee per order with printed books

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}

# S3-compatible object storage (S3, Cloudflare R2, MinIO) when configured.
AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME", default="")
if AWS_STORAGE_BUCKET_NAME:
    AWS_S3_ENDPOINT_URL = env("AWS_S3_ENDPOINT_URL", default=None) or None
    AWS_ACCESS_KEY_ID = env("AWS_ACCESS_KEY_ID", default="")
    AWS_SECRET_ACCESS_KEY = env("AWS_SECRET_ACCESS_KEY", default="")
    AWS_QUERYSTRING_AUTH = False
    STORAGES["default"] = {"BACKEND": "storages.backends.s3.S3Storage"}

# Upload limits (enforced in media_library API)
MAX_UPLOAD_MB = env.int("MAX_UPLOAD_MB", default=200)

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Channels (real-time) -------------------------------------------------
REDIS_URL = env("REDIS_URL", default="")
if REDIS_URL:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {"hosts": [REDIS_URL]},
        }
    }
else:
    # Single-process only; fine for local development.
    CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}

# --- Celery ---------------------------------------------------------------
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default=REDIS_URL or "redis://localhost:6379/1")
CELERY_RESULT_BACKEND = CELERY_BROKER_URL
CELERY_TASK_ALWAYS_EAGER = env.bool("CELERY_TASK_ALWAYS_EAGER", default=not REDIS_URL)

# --- Payments -------------------------------------------------------------
PAYMENT_PROVIDER = env("PAYMENT_PROVIDER", default="dummy")
DEFAULT_CURRENCY = env("DEFAULT_CURRENCY", default="USD")


# --- Security -------------------------------------------------------------
# Browser-side protections (the CSP and other headers live in apps/core/security.py).
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_AGE = 60 * 60 * 24 * 14  # stay signed in for two weeks
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
X_FRAME_OPTIONS = "DENY"
DATA_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024  # non-file request bodies
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
DATA_UPLOAD_MAX_NUMBER_FIELDS = 500
# Passwords are hashed (never stored readable). Django's default is PBKDF2-SHA256.

# Rate limits (per IP, per minute) and sign-in lockout.
RATE_LIMIT_PER_MIN = env.int("RATE_LIMIT_PER_MIN", default=240)
RATE_LIMIT_SENSITIVE_PER_MIN = env.int("RATE_LIMIT_SENSITIVE_PER_MIN", default=12)
LOGIN_MAX_FAILURES = env.int("LOGIN_MAX_FAILURES", default=6)
LOGIN_LOCKOUT_SECONDS = env.int("LOGIN_LOCKOUT_SECONDS", default=15 * 60)
# Only true when a proxy you control (Nginx, a load balancer) sets X-Forwarded-For. Otherwise
# anyone could fake their address and dodge the limits.
TRUST_PROXY_HEADERS = env.bool("TRUST_PROXY_HEADERS", default=False)

# Shared counters across processes when Redis is available.
if REDIS_URL:
    CACHES = {"default": {"BACKEND": "django.core.cache.backends.redis.RedisCache", "LOCATION": REDIS_URL}}
