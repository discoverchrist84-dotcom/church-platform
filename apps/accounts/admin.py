from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group
from django.utils.html import format_html

from apps.core.admin_base import ExportCsvMixin
from apps.core.roles import ADMIN_GROUP, EDITOR_GROUP, MODERATOR_GROUP, ensure_roles

from .models import User


def _superusers_only(modeladmin, request):
    if request.user.is_superuser:
        return True
    modeladmin.message_user(request, "Only a full administrator can change who has admin access.", messages.ERROR)
    return False


@admin.register(User)
class CustomUserAdmin(ExportCsvMixin, UserAdmin):
    save_on_top = True
    list_per_page = 25
    change_list_template = "admin/church/change_list.html"
    change_form_template = "admin/church/change_form.html"
    list_display = ("username", "email", "first_name", "last_name", "access", "is_active", "last_login")
    list_filter = ("is_staff", "is_superuser", "is_active", "groups")
    search_fields = ("username", "email", "first_name", "last_name")
    actions = ["make_full_admin", "make_church_admin", "make_editor", "make_moderator", "remove_admin_access",
               "deactivate", "activate"]
    fieldsets = UserAdmin.fieldsets + (("Church", {"fields": ("phone", "avatar", "bio")}),)
    add_fieldsets = UserAdmin.add_fieldsets + ((None, {"fields": ("email", "first_name", "last_name")}),)

    HELP_LIST = ("Everyone with an account. To give someone administrator access, tick them and use the Action menu: "
                 "“Give full admin access” lets them do everything; the other roles allow only part of the admin. "
                 "To stop someone signing in without deleting their history, use “Deactivate”.")
    HELP_FORM = ("‘Active’ = may sign in. ‘Staff status’ = may open this admin. ‘Superuser’ = may do everything. "
                 "Groups give a ready-made set of permissions (Church administrators, Content editors, Moderators).")

    def changelist_view(self, request, extra_context=None):
        return super().changelist_view(request, {"admin_help": self.HELP_LIST, "model_label": "users", **(extra_context or {})})

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        return super().changeform_view(request, object_id, form_url,
                                       {"admin_help": self.HELP_FORM, "model_label": "user", **(extra_context or {})})

    @admin.display(description="Access level")
    def access(self, obj):
        if obj.is_superuser:
            return format_html('<b style="color:#b45309">Full administrator</b>')
        names = [g.name for g in obj.groups.all()]
        if obj.is_staff:
            return ", ".join(names) or "Staff"
        return "Member"

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("groups")

    # --- one-click roles ----------------------------------------------------
    def _set_role(self, request, queryset, *, superuser, staff, group=None, label=""):
        if not _superusers_only(self, request):
            return
        ensure_roles()  # make sure the role groups exist (they are normally created by `migrate`)
        done = 0
        for u in queryset:
            if u == request.user and not superuser:
                self.message_user(request, "You cannot lower your own access. Ask another administrator.", messages.WARNING)
                continue
            u.is_superuser, u.is_staff = superuser, staff
            u.save(update_fields=["is_superuser", "is_staff"])
            u.groups.clear()
            if group:
                u.groups.add(Group.objects.get(name=group))
            done += 1
        self.message_user(request, f"{done} user(s) now: {label}.", messages.SUCCESS)

    @admin.action(description="Give FULL admin access (can do everything)", permissions=["change"])
    def make_full_admin(self, request, queryset):
        self._set_role(request, queryset, superuser=True, staff=True, label="full administrator")

    @admin.action(description="Make Church administrator (all church content and people)", permissions=["change"])
    def make_church_admin(self, request, queryset):
        self._set_role(request, queryset, superuser=False, staff=True, group=ADMIN_GROUP, label="church administrator")

    @admin.action(description="Make Content editor (add and edit, no deleting)", permissions=["change"])
    def make_editor(self, request, queryset):
        self._set_role(request, queryset, superuser=False, staff=True, group=EDITOR_GROUP, label="content editor")

    @admin.action(description="Make Moderator (review posts and reports)", permissions=["change"])
    def make_moderator(self, request, queryset):
        self._set_role(request, queryset, superuser=False, staff=True, group=MODERATOR_GROUP, label="moderator")

    @admin.action(description="Remove admin access (back to an ordinary member)", permissions=["change"])
    def remove_admin_access(self, request, queryset):
        self._set_role(request, queryset, superuser=False, staff=False, label="ordinary member")

    @admin.action(description="Deactivate (cannot sign in; history is kept)", permissions=["change"])
    def deactivate(self, request, queryset):
        n = queryset.exclude(pk=request.user.pk).update(is_active=False)
        self.message_user(request, f"{n} account(s) deactivated.", messages.SUCCESS)

    @admin.action(description="Activate (may sign in again)", permissions=["change"])
    def activate(self, request, queryset):
        n = queryset.update(is_active=True)
        self.message_user(request, f"{n} account(s) activated.", messages.SUCCESS)
