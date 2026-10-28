"""Ready-made admin roles (permission groups), created automatically after `migrate`.

* Superuser ............ can do everything (set with the "Give full admin access" action).
* Church administrators  everything on the church's content, people and website settings, but not Django's own system tables.
* Content editors ...... add/change history, events, announcements, sermons, leaders and councils (no deleting).
* Moderators ........... review posts, comments, prayer requests and reports (hide / resolve, no deleting).
"""
import logging

from django.contrib.auth.models import Group, Permission

log = logging.getLogger(__name__)

CHURCH_APPS = ["core", "accounts", "churches", "leadership", "history", "community", "media_library", "giving", "bookstore", "realtime"]
ADMIN_GROUP = "Church administrators"
EDITOR_GROUP = "Content editors"
MODERATOR_GROUP = "Moderators"

EDITOR_MODELS = {
    "history": None,  # None = every model in the app
    "leadership": None,
    "churches": {"branchleader"},
    "community": {"announcement", "event", "ministry"},
    "media_library": None,
    "bookstore": {"book", "author", "category", "chapter", "devotionalentry"},
}
MODERATOR_MODELS = {"community": {"post", "comment", "prayerrequest", "report"}}


def _perms(spec, actions):
    out = []
    for app, models in spec.items():
        qs = Permission.objects.filter(content_type__app_label=app)
        if models is not None:
            qs = qs.filter(content_type__model__in=models)
        out.extend(p for p in qs if p.codename.split("_", 1)[0] in actions)
    return out


def ensure_roles():
    """Create or refresh the three groups. Safe to run any number of times."""
    everything = {a: None for a in CHURCH_APPS}
    admins, _ = Group.objects.get_or_create(name=ADMIN_GROUP)
    admins.permissions.set(_perms(everything, {"add", "change", "delete", "view"}))
    editors, _ = Group.objects.get_or_create(name=EDITOR_GROUP)
    editors.permissions.set(_perms(EDITOR_MODELS, {"add", "change", "view"}))
    mods, _ = Group.objects.get_or_create(name=MODERATOR_GROUP)
    mods.permissions.set(_perms(MODERATOR_MODELS, {"change", "view"}))


def on_post_migrate(sender, **kwargs):
    """Runs after `migrate`. Permissions are created per app, so make sure they all exist first."""
    from django.apps import apps as global_apps
    from django.contrib.auth.management import create_permissions
    from django.contrib.contenttypes.management import create_contenttypes
    from django.db import DatabaseError

    if getattr(sender, "label", "") != "core":
        return
    try:
        for config in global_apps.get_app_configs():
            if config.label in CHURCH_APPS:
                create_contenttypes(config, verbosity=0)
                create_permissions(config, verbosity=0)
        ensure_roles()
    except DatabaseError:  # e.g. migrating a single app on an empty database
        log.warning("Could not create admin roles yet; they are created on the next full migrate.")
