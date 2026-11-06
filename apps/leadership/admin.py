from django.contrib import admin
from django.utils.html import format_html

from apps.core.admin_base import FriendlyAdmin, flag_action, picture_preview, safe_url

from django.utils.translation import gettext_lazy as _

from .models import Council, CouncilMember


class TermFilter(admin.SimpleListFilter):
    title = _("term")
    parameter_name = "term"

    def lookups(self, request, model_admin):
        return [("ended", "Term ended: election due"), ("soon", "Ends within 6 months"), ("serving", "Serving")]

    def queryset(self, request, queryset):
        v = self.value()
        if not v:
            return queryset
        ids = [m.pk for m in queryset.filter(is_current=True) if m.election_status == {"ended": "term ended", "soon": "election due soon", "serving": "serving"}[v]]
        return queryset.filter(pk__in=ids)


class MemberInline(admin.StackedInline):
    model = CouncilMember
    extra = 0
    verbose_name_plural = "Members and their offices"
    readonly_fields = ("photo_preview",)
    fields = (("name", "title"), ("photo", "photo_preview"), "bio", ("elected_on", "term_start", "term_end", "is_current", "order"),
              ("email", "phone", "show_contact"))


    @admin.display(description="Saved photo")
    def photo_preview(self, obj):
        return picture_preview(obj, "photo")


@admin.register(Council)
class CouncilAdmin(FriendlyAdmin):
    help_list = "Councils such as the General Council. Open one to add or change its members and offices."
    help_form = ("Leave 'Branch' empty for a church-wide council, or pick a unit for a council of that unit. "
                 "Add each member below with their office, photo and a short biography. Lower 'order' numbers show first.")
    list_display = ("name", "scope", "member_count", "order", "is_active")
    list_editable = ("order", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}
    autocomplete_fields = ("branch",)
    inlines = [MemberInline]
    readonly_fields = ("cover_preview",)
    fieldsets = (
        (None, {"fields": ("name", "slug", "branch", "description", "order", "is_active")}),
        ("Group picture (optional)", {
            "description": "One picture for the whole council. It shows on the Leadership page above the members. "
                           "Pictures of individual people are added to each member below.",
            "fields": (("cover", "cover_preview"),),
        }),
    )

    @admin.display(description="Saved picture")
    def cover_preview(self, obj):
        return picture_preview(obj, "cover")
    actions = [
        flag_action("is_active", False, "Hide selected from the website", "%(n)d council hidden.", "%(n)d councils hidden."),
        flag_action("is_active", True, "Show selected on the website", "%(n)d council shown.", "%(n)d councils shown."),
    ]

    @admin.display(description="Applies to")
    def scope(self, obj):
        return obj.branch.name if obj.branch_id else "Whole church (general)"

    @admin.display(description="Members")
    def member_count(self, obj):
        return obj.members.count()


@admin.register(CouncilMember)
class CouncilMemberAdmin(FriendlyAdmin):
    help_list = "Everyone who serves on a council. Tip: it is quicker to edit members from inside their council."
    help_form = "Only administrators edit this. Set the date the person took office; the site shows when the 4-year term ends and flags it on the dashboard for an election. Choose the council, then enter the name, office and a photo. Contact details stay private unless 'show contact' is ticked."
    list_display = ("thumb", "name", "title", "council", "term", "election_status", "is_current", "order")
    list_display_links = ("thumb", "name")
    list_editable = ("order",)
    list_filter = ("council", "is_current", TermFilter)
    search_fields = ("name", "title")
    readonly_fields = ("photo_preview",)
    fields = (("name", "title"), "council", ("photo", "photo_preview"), "bio", ("elected_on", "term_start", "term_end", "is_current", "order"),
              ("email", "phone", "show_contact"))

    @admin.display(description="Saved photo")
    def photo_preview(self, obj):
        return picture_preview(obj, "photo")

    @admin.display(description="Term")
    def term(self, obj):
        return obj.tenure or "—"

    @admin.display(description="Status")
    def election_status(self, obj):
        return obj.election_status or "—"

    @admin.display(description="")
    def thumb(self, obj):
        url = safe_url(obj.photo)
        return format_html('<img src="{}" class="athumb">', url) if url else "👤"
