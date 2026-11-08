from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"

    def ready(self):
        from django.db.models.signals import post_migrate

        from . import security  # noqa: F401  (registers the sign-in failure counters)
        from .roles import on_post_migrate

        from .images import connect_all

        connect_all()  # pictures are resized automatically on upload
        post_migrate.connect(on_post_migrate, dispatch_uid="church_admin_roles")
