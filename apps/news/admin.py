from django.contrib import admin
from django.utils.html import format_html

from apps.core.admin_base import FriendlyAdmin, flag_action, picture_preview

from .models import NewsArticle


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
        url = obj.image.url if obj.image and obj.image.storage.exists(obj.image.name) else ""
        return format_html('<img src="{}" class="athumb">', url) if url else "📰"

    @admin.display(description="Saved picture")
    def image_preview(self, obj):
        return picture_preview(obj, "image")
