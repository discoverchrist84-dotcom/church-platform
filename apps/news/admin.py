from django.contrib import admin
from django.utils.html import format_html

from apps.core.admin_base import FriendlyAdmin, flag_action, picture_preview, safe_url

from .models import Bulletin, NewsArticle


@admin.register(NewsArticle)
class NewsArticleAdmin(FriendlyAdmin):
    help_list = ("News shown on the News page and the home page. Use the filters to see church news or outside news. "
                 "Untick 'published' to keep a story as a draft.")
    help_form = ("Write the headline, a short summary and the story. Choose 'In our church' for our own news, or 'Outside the church' "
                 "for news from other churches, the community, the nation or the world (add the source). "
                 "To schedule a story, set 'publish on' to a future time.")
    list_display = ("thumb", "title", "scope", "topic", "branch", "published_at", "is_pinned", "is_published")
    list_display_links = ("thumb", "title")
    list_editable = ("is_pinned", "is_published")
    list_filter = ("is_published", "scope", "topic", "is_pinned")
    search_fields = ("title", "summary", "body", "place")
    date_hierarchy = "published_at"
    autocomplete_fields = ("branch",)
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = ("image_preview",)
    actions = [
        flag_action("is_published", True, "Publish selected", "%(n)d story published.", "%(n)d stories published."),
        flag_action("is_published", False, "Move selected back to drafts", "%(n)d story hidden.", "%(n)d stories hidden."),
    ]
    fieldsets = (
        ("The story", {"fields": ("title", "slug", "summary", "body")}),
        ("Picture", {"fields": (("image", "image_preview"),)}),
        ("Where it belongs", {"fields": ("scope", "topic", "branch", "place")}),
        ("Source (for outside news)", {"classes": ("collapse",), "fields": ("author_name", "source_name", "source_url")}),
        ("Publishing", {"fields": ("is_published", "published_at", "is_pinned")}),
    )

    @admin.display(description="")
    def thumb(self, obj):
        url = safe_url(obj.image)
        return format_html('<img src="{}" class="athumb">', url) if url else "📰"

    @admin.display(description="Saved picture")
    def image_preview(self, obj):
        return picture_preview(obj, "image")


@admin.register(Bulletin)
class BulletinAdmin(FriendlyAdmin):
    help_list = ("Official notices from the National Headquarters. Send one to the whole church, or only to chosen areas, districts or stations. "
                 "Members get a notification when it is published.")
    help_form = ("Write the notice and choose who receives it. For 'Chosen', pick the areas, districts or stations: everything beneath them "
                 "receives it too. The notification is sent once, when you save a published notice.")
    list_display = ("title", "audience", "target_names", "is_urgent", "published_at", "notified", "is_published")
    list_editable = ("is_urgent", "is_published")
    list_filter = ("audience", "is_urgent", "is_published")
    search_fields = ("title", "body")
    date_hierarchy = "published_at"
    filter_horizontal = ("units",)
    readonly_fields = ("notified_at",)
    fieldsets = (
        ("The notice", {"fields": ("title", "body", "is_urgent")}),
        ("Who receives it", {"fields": ("audience", "units")}),
        ("Publishing", {"fields": ("is_published", "published_at", "send_notification", "notified_at")}),
    )
    actions = ["resend"]

    @admin.display(description="Sent to")
    def target_names(self, obj):
        if obj.audience == obj.Audience.ALL:
            return "Everyone"
        names = [u.name for u in obj.units.all()[:4]]
        return ", ".join(names) + ("…" if obj.units.count() > 4 else "")

    @admin.display(description="Notified", boolean=True)
    def notified(self, obj):
        return bool(obj.notified_at)

    def save_model(self, request, obj, form, change):
        if not obj.author_id:
            obj.author = request.user
        super().save_model(request, obj, form, change)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)  # the chosen units are saved now
        obj = form.instance
        n = obj.send_notifications()
        if n:
            self.message_user(request, f"Notification sent to {n} member(s).")

    @admin.action(description="Send the notification again to the audience")
    def resend(self, request, queryset):
        total = 0
        for b in queryset:
            Bulletin.objects.filter(pk=b.pk).update(notified_at=None)
            b.refresh_from_db()
            total += b.send_notifications()
        self.message_user(request, f"Notifications sent: {total}.")
