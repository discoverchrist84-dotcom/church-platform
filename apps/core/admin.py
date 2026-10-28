from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin
from django.contrib.auth.models import Group

from .admin_base import FriendlyAdmin, SingletonAdmin, picture_preview
from .models import SiteSettings

admin.site.unregister(Group)


@admin.register(Group)
class RoleAdmin(FriendlyAdmin, GroupAdmin):
    help_list = ("Roles are ready-made sets of permissions. Church administrators, Content editors and Moderators are created "
                 "automatically. Give someone a role from the Users page.")
    help_form = "Move permissions from ‘Available’ to ‘Chosen’. Most of the time you do not need to edit these."


@admin.register(SiteSettings)
class SiteSettingsAdmin(SingletonAdmin):
    help_list = "The website's name, logo, banner and contact details."
    help_form = ("This is the control room for how the website introduces itself. Work down the page: name and logo, "
                 "the announcement banner, then contact details. Anything you leave blank keeps its normal default. "
                 "Press Save at the top or bottom: changes show on the website within about a minute.")
    readonly_fields = ("logo_preview",)
    fieldsets = (
        ("1 · Church name", {
            "description": "How the church is named in the header, the footer and on a phone when the app is installed.",
            "fields": ("church_name", "brand", "sub_brand", "short_name"),
        }),
        ("2 · Logo", {
            "description": "Choose a square PNG or JPG (at least 256×256), press Save, and the preview appears. "
                           "It replaces the logo in the header and on the home page.",
            "fields": (("logo", "logo_preview"),),
        }),
        ("3 · Words on the home page", {"fields": ("welcome_text", "tagline")}),
        ("4 · Announcement banner", {
            "description": "A coloured strip across the top of every page, for something everyone should see. Tick the box to show it.",
            "fields": ("banner_is_active", "banner_text", "banner_link"),
        }),
        ("5 · Contact details (shown in the footer)", {"fields": ("contact_email", "contact_phone", "address", "footer_note")}),
        ("6 · Bookshop payments", {
            "description": "Where buyers should send a bank transfer for books. Shown on their order page.",
            "fields": ("payment_instructions",),
        }),
        ("7 · Social media links", {"classes": ("collapse",), "fields": ("facebook_url", "youtube_url", "instagram_url", "x_url", "whatsapp_url")}),
    )

    @admin.display(description="Saved logo")
    def logo_preview(self, obj):
        return picture_preview(obj, "logo")
