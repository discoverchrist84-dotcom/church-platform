from django.contrib import admin, messages

from apps.core.admin_base import FriendlyAdmin, flag_action

from .models import Announcement, Comment, Event, EventRSVP, Ministry, Post, PrayerRequest, Report

hide = lambda label: flag_action("is_hidden", True, f"Hide selected {label} from members", "%(n)d hidden.", "%(n)d hidden.")  # noqa: E731
unhide = lambda label: flag_action("is_hidden", False, f"Show selected {label} again", "%(n)d shown.", "%(n)d shown.")  # noqa: E731


@admin.register(Announcement)
class AnnouncementAdmin(FriendlyAdmin):
    help_list = "News shown on a unit's page. Pinned announcements stay at the top."
    help_form = "Write the headline and message, choose the unit it is for, and tick 'published' when it should appear."
    list_display = ("title", "branch", "is_pinned", "is_published", "created_at")
    list_editable = ("is_pinned", "is_published")
    list_filter = ("is_published", "is_pinned", "branch__level")
    search_fields = ("title", "body", "branch__name")
    autocomplete_fields = ("branch",)
    date_hierarchy = "created_at"
    actions = [
        flag_action("is_published", True, "Publish selected", "%(n)d published.", "%(n)d published."),
        flag_action("is_published", False, "Unpublish selected (hide, keep)", "%(n)d unpublished.", "%(n)d unpublished."),
    ]


class RSVPInline(admin.TabularInline):
    model = EventRSVP
    extra = 0
    verbose_name_plural = "Who is coming"


@admin.register(Event)
class EventAdmin(FriendlyAdmin):
    help_list = "Services, conferences and gatherings. Upcoming events appear on the website automatically."
    help_form = "Give the event a title, the unit hosting it, the start time and place. Set a capacity to limit RSVPs."
    list_display = ("title", "branch", "starts_at", "location", "capacity")
    list_filter = ("branch__level",)
    search_fields = ("title", "description", "branch__name")
    autocomplete_fields = ("branch",)
    date_hierarchy = "starts_at"
    inlines = [RSVPInline]


@admin.register(Ministry)
class MinistryAdmin(FriendlyAdmin):
    help_list = "Groups inside a unit, such as the choir, youth or women's fellowship."
    help_form = "Name the group, choose its unit and pick the members."
    list_display = ("name", "branch")
    list_filter = ("branch__level",)
    search_fields = ("name", "branch__name")
    autocomplete_fields = ("branch",)
    prepopulated_fields = {"slug": ("name",)}
    filter_horizontal = ("members",)


@admin.register(Post)
class PostAdmin(FriendlyAdmin):
    help_list = "Board posts written by members. Hide a post to remove it from view without deleting it."
    help_form = "Tick 'hidden' to take this post off the board."
    list_display = ("title", "branch", "author", "is_hidden", "created_at")
    list_editable = ("is_hidden",)
    list_filter = ("is_hidden", "branch__level")
    search_fields = ("title", "body", "author__username")
    date_hierarchy = "created_at"
    actions = [hide("posts"), unhide("posts")]


@admin.register(Comment)
class CommentAdmin(FriendlyAdmin):
    help_list = "Comments on board posts. Hide any that are inappropriate."
    list_display = ("post", "author", "is_hidden", "created_at")
    list_editable = ("is_hidden",)
    list_filter = ("is_hidden",)
    search_fields = ("body", "author__username")
    actions = [hide("comments"), unhide("comments")]


@admin.register(PrayerRequest)
class PrayerRequestAdmin(FriendlyAdmin):
    help_list = "Prayer wall requests. Anonymous requests still record the author here for safety, but never show it publicly."
    list_display = ("branch", "author", "is_anonymous", "is_answered", "is_hidden", "created_at")
    list_editable = ("is_hidden",)
    list_filter = ("is_answered", "is_hidden", "branch__level")
    search_fields = ("body", "author__username")
    actions = [hide("prayer requests"), unhide("prayer requests")]


@admin.register(Report)
class ReportAdmin(FriendlyAdmin):
    help_list = "Content that members flagged. Read the reason, then either hide the content or mark the report resolved."
    help_form = "Tick 'resolved' once you have dealt with this report."
    list_display = ("summary", "reason", "branch", "reporter", "resolved", "created_at")
    list_filter = ("resolved", "branch__level")
    search_fields = ("reason",)
    readonly_fields = ("reported_text",)
    actions = ["hide_reported_and_resolve", "mark_resolved", "mark_open"]

    @admin.display(description="What was reported")
    def summary(self, obj):
        return f"{obj.target_kind.title()}: {obj.target_text[:60]}" if obj.target else f"{obj.target_kind.title()} (removed)"

    @admin.display(description="Reported content")
    def reported_text(self, obj):
        return obj.target_text or "(nothing: the content has been removed)"

    @admin.action(description="Hide the reported content and mark resolved", permissions=["change"])
    def hide_reported_and_resolve(self, request, queryset):
        n = 0
        for r in queryset:
            t = r.target
            if t is not None and hasattr(t, "is_hidden"):
                t.is_hidden = True
                t.save(update_fields=["is_hidden"])
            r.resolved, r.resolved_by = True, request.user
            r.save()
            n += 1
        self.message_user(request, f"{n} report(s) resolved and the content hidden.", messages.SUCCESS)

    @admin.action(description="Mark selected as resolved", permissions=["change"])
    def mark_resolved(self, request, queryset):
        n = queryset.update(resolved=True, resolved_by=request.user)
        self.message_user(request, f"{n} report(s) marked resolved.", messages.SUCCESS)

    @admin.action(description="Re-open selected", permissions=["change"])
    def mark_open(self, request, queryset):
        n = queryset.update(resolved=False, resolved_by=None)
        self.message_user(request, f"{n} report(s) re-opened.", messages.SUCCESS)


@admin.register(EventRSVP)
class EventRSVPAdmin(FriendlyAdmin):
    help_list = "Who said they are coming to which event."
    list_display = ("event", "user", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("event__title", "user__username", "user__email")
    autocomplete_fields = ("event", "user")
