from .base import *  # noqa: F401,F403
from .base import env

DEBUG = env.bool("DEBUG", default=True)
ALLOWED_HOSTS = ["*"]
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Serve static files straight from /static without running collectstatic.
WHITENOISE_USE_FINDERS = True
WHITENOISE_AUTOREFRESH = True
