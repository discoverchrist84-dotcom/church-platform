from django.contrib import admin

from apps.core.admin_base import FriendlyAdmin, flag_action

from .models import MediaAsset, Sermon


@admin.register(Sermon)
class SermonAdmin(FriendlyAdmin):
    help_list = "Messages members can watch or listen to. Untick 'published' to hide one without deleting it."
    help_form = "Enter the title, speaker and date, then either paste a YouTube/Vimeo link or choose an uploaded file."
    list_display = ("title", "speaker", "branch", "preached_on", "is_published")
    list_editable = ("is_published",)
    list_filter = ("is_published", "branch__level")
    search_fields = ("title", "speaker", "scripture", "branch__name")
    autocomplete_fields = ("branch", "asset")
    date_hierarchy = "preached_on"
    actions = [
        flag_action("is_published", True, "Publish selected", "%(n)d published.", "%(n)d published."),
        flag_action("is_published", False, "Unpublish selected (hide, keep)", "%(n)d unpublished.", "%(n)d unpublished."),
    ]


@admin.register(MediaAsset)
class MediaAssetAdmin(FriendlyAdmin):
    help_list = "Every uploaded audio, video, image or document. Deleting a file here removes it from any sermon using it."
    list_display = ("original_name", "kind", "branch", "owner", "size_display", "created_at")
    list_filter = ("kind", "branch__level")
    search_fields = ("original_name",)
    date_hierarchy = "created_at"

    @admin.display(description="Size", ordering="size")
    def size_display(self, obj):
        mb = obj.size / (1024 * 1024)
        return f"{mb:.1f} MB" if mb >= 1 else f"{obj.size / 1024:.0f} KB"
