from django.contrib import admin

from apps.core.admin_base import FriendlyAdmin

from apps.core.models import PublishStatus

from .models import Document, Era, Figure, HistoricalEvent, Place, Source, Tag


@admin.action(description="Publish selected (make visible on the website)", permissions=["change"])
def make_published(modeladmin, request, queryset):
    for obj in queryset:
        obj.status = PublishStatus.PUBLISHED
        obj.save()  # goes through save() so published_at is set


@admin.action(description="Move selected back to draft (hide, keep)", permissions=["change"])
def make_draft(modeladmin, request, queryset):
    for obj in queryset:
        obj.status = PublishStatus.DRAFT
        obj.save()


@admin.register(Era)
class EraAdmin(FriendlyAdmin):
    help_list = "Periods of church history that group events on the timeline."
    list_display = ("name", "start_year", "end_year")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Tag)
class TagAdmin(FriendlyAdmin):
    help_list = "Short labels used to find related history events."
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)


@admin.register(Source)
class SourceAdmin(FriendlyAdmin):
    help_list = "Books, articles and references. Attach them to events so every claim has a source."
    list_display = ("title", "author", "kind", "year")
    list_filter = ("kind",)
    search_fields = ("title", "author", "publication")


@admin.register(Place)
class PlaceAdmin(FriendlyAdmin):
    help_list = "Places connected to events in the history."
    list_display = ("name", "modern_name")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name", "modern_name")


@admin.register(Figure)
class FigureAdmin(FriendlyAdmin):
    help_list = "People who shaped the church. Only published entries show on the website."
    help_form = "Fill in the biography, attach sources, and set the status to Published when it is ready."
    list_display = ("name", "title", "born_year", "died_year", "status")
    list_filter = ("status",)
    search_fields = ("name", "title", "bio")
    prepopulated_fields = {"slug": ("name",)}
    filter_horizontal = ("sources",)
    actions = [make_published, make_draft]


@admin.register(HistoricalEvent)
class HistoricalEventAdmin(FriendlyAdmin):
    help_list = "The church timeline. New events start as Draft and only appear once Published."
    help_form = "Write a short summary and the full article, link people, places and sources, and set the status to Published when ready."
    list_display = ("title", "era", "year_start", "status", "published_at")
    list_filter = ("status", "era", "tags")
    search_fields = ("title", "summary", "body")
    prepopulated_fields = {"slug": ("title",)}
    filter_horizontal = ("figures", "places", "sources", "tags")
    date_hierarchy = "published_at"
    actions = [make_published, make_draft]
    fieldsets = (
        (None, {"fields": ("title", "slug", "era", "status")}),
        ("When", {"fields": ("year_start", "year_end", "date_display")}),
        ("Content", {"fields": ("summary", "body", "hero_image")}),
        ("Relations & citations", {"fields": ("figures", "places", "tags", "sources")}),
    )


@admin.register(Document)
class DocumentAdmin(FriendlyAdmin):
    help_list = "Creeds, council decisions, letters and other primary texts."
    list_display = ("title", "kind", "year", "status")
    list_filter = ("kind", "status")
    search_fields = ("title", "text")
    prepopulated_fields = {"slug": ("title",)}
    actions = [make_published, make_draft]
