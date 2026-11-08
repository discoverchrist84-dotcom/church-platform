from django.contrib.admin.apps import AdminConfig


class ChurchAdminConfig(AdminConfig):
    """Swap Django's admin site for ours (apps/core/admin_site.py)."""

    default_site = "apps.core.admin_site.ChurchAdminSite"
