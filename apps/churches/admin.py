from django.contrib import admin
from django.utils.html import format_html

from apps.core.admin_base import FriendlyAdmin, flag_action, picture_preview, safe_url

from .models import Branch, BranchLeader, Membership


class PostingFilter(admin.SimpleListFilter):
    title = "transfer status"
    parameter_name = "posting"

    def lookups(self, request, model_admin):
        return [("overdue", "Overdue for transfer"), ("soon", "Due within 6 months"), ("serving", "Serving")]

    def queryset(self, request, queryset):
        v = self.value()
        if not v:
            return queryset
        want = {"overdue": "overdue", "soon": "due soon", "serving": "serving"}[v]
        return queryset.filter(pk__in=[o.pk for o in queryset.filter(is_current=True) if o.posting_status == want])


class LeaderInline(admin.StackedInline):
    model = BranchLeader
    extra = 0
    verbose_name = "leader"
    verbose_name_plural = "Leaders: superintendent (areas and districts), pastor (stations) and other officers"
    fields = (("name", "role", "title"), ("photo", "photo_preview"), "bio", ("posted_on", "ended_on", "is_current", "order"),
              ("phone", "email", "show_contact"))
    readonly_fields = ("photo_preview",)

    @admin.display(description="Saved photo")
    def photo_preview(self, obj):
        return picture_preview(obj, "photo")


class MembershipInline(admin.TabularInline):
    model = Membership
    extra = 0
    autocomplete_fields = ("user",)
    verbose_name_plural = "People who belong to this unit (only an administrator can give someone a management role)"


@admin.register(Branch)
class BranchAdmin(FriendlyAdmin):
    help_list = ("Every unit of the church: areas, districts and stations (local churches). Use the filters on the right "
                 "to show just one type. The National Headquarters is the station marked with ★.")
    help_form = ("Choose what kind of unit this is, then where it belongs: an area stands on its own, a district goes under an "
                 "area, a station under a district. Tick 'National Headquarters' on the one station that is the headquarters. "
                 "Add its superintendent or pastor further down the page.")
    list_display = ("name", "serial", "level", "parent", "hq_mark", "head", "city", "country", "is_active")
    list_editable = ("is_active",)
    list_filter = ("level", "is_national_headquarters", "is_active", "country")
    search_fields = ("name", "city", "country")
    prepopulated_fields = {"slug": ("name",)}
    list_select_related = ("parent",)
    autocomplete_fields = ("parent",)
    inlines = [LeaderInline, MembershipInline]
    actions = [
        flag_action("is_active", False, "Hide selected from the website (deactivate)", "%(n)d unit hidden.", "%(n)d units hidden."),
        flag_action("is_active", True, "Show selected on the website (activate)", "%(n)d unit shown.", "%(n)d units shown."),
    ]
    fieldsets = (
        ("Where it sits", {
            "description": "Area (top level) → District → Station (a local church). Areas have no parent. "
                           "The National Headquarters is a station: tick the box below on that one station.",
            "fields": ("name", "slug", "level", "parent", "serial", "is_national_headquarters", "is_active"),
        }),
        ("About", {"fields": ("description", "service_times")}),
        ("Pictures", {"description": "Upload, press Save, and the picture shows on the unit's page and below.",
                      "fields": (("logo", "logo_preview"), ("cover", "cover_preview"))}),
        ("Location", {"classes": ("collapse",), "fields": ("address", "city", "region", "country", "latitude", "longitude")}),
        ("Contact", {"classes": ("collapse",), "fields": ("phone", "email", "website")}),
    )

    readonly_fields = ("logo_preview", "cover_preview")

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("leaders")

    @admin.display(description="Saved logo")
    def logo_preview(self, obj):
        return picture_preview(obj, "logo")

    @admin.display(description="Saved cover")
    def cover_preview(self, obj):
        return picture_preview(obj, "cover")

    @admin.display(description="HQ", ordering="is_national_headquarters")
    def hq_mark(self, obj):
        return "★ National HQ" if obj.is_national_headquarters else ""

    @admin.display(description="Led by")
    def head(self, obj):
        leader = obj.superintendent
        return leader.name if leader else "—"


@admin.register(BranchLeader)
class BranchLeaderAdmin(FriendlyAdmin):
    help_list = "Superintendents (areas and districts), pastors (stations) and other officers. Ministers are posted for 4 years. Untick 'current' when someone steps down, so their history is kept."
    help_form = ("Only administrators add or change ministers. Pick the unit and the role, and enter the date the minister was posted: the site "
                 "works out the 4-year transfer date. To transfer someone, untick 'current' (their history is kept) and add the next minister.")
    list_display = ("thumb", "name", "role", "branch", "posted_on", "transfer_due", "posting", "is_current")
    list_display_links = ("thumb", "name")
    list_filter = ("role", "is_current", "branch__level", PostingFilter)
    search_fields = ("name", "branch__name")
    autocomplete_fields = ("branch",)
    actions = ["end_posting"]

    @admin.display(description="Transfer due")
    def transfer_due(self, obj):
        d = obj.transfer_due_on
        return d.strftime("%b %Y") if d else "—"

    @admin.display(description="Posting")
    def posting(self, obj):
        return obj.posting_status or "—"

    @admin.action(description="Transfer: end the posting of selected ministers (history is kept)")
    def end_posting(self, request, queryset):
        n = 0
        for obj in queryset.filter(is_current=True):
            obj.is_current = False
            obj.save()
            n += 1
        self.message_user(request, f"{n} posting(s) ended. Add the new minister for each unit.")

    @admin.display(description="")
    def thumb(self, obj):
        url = safe_url(obj.photo)
        return format_html('<img src="{}" class="athumb">', url) if url else "👤"


@admin.register(Membership)
class MembershipAdmin(FriendlyAdmin):
    help_list = "Which people belong to which unit. A branch 'admin' can manage that unit and everything beneath it."
    help_form = "Choose the person, the unit and their role there."
    list_display = ("user", "branch", "role", "is_primary", "created_at")
    list_filter = ("role", "branch__level")
    search_fields = ("user__username", "user__email", "branch__name")
    autocomplete_fields = ("user", "branch")
