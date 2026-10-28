from django.contrib import admin

from apps.core.admin_base import FriendlyAdmin, flag_action

from .models import Donation, Fund


@admin.register(Fund)
class FundAdmin(FriendlyAdmin):
    help_list = "The purposes people can give to. Untick 'active' to stop accepting gifts for a fund without losing its history."
    help_form = "Leave 'branch' empty for a church-wide fund, or choose a unit to make it that unit's fund."
    list_display = ("name", "branch", "is_active")
    list_editable = ("is_active",)
    list_filter = ("is_active", "branch__level")
    search_fields = ("name", "branch__name")
    autocomplete_fields = ("branch",)
    prepopulated_fields = {"slug": ("name",)}
    actions = [
        flag_action("is_active", False, "Stop accepting gifts for selected", "%(n)d fund closed.", "%(n)d funds closed."),
        flag_action("is_active", True, "Accept gifts for selected", "%(n)d fund opened.", "%(n)d funds opened."),
    ]


@admin.register(Donation)
class DonationAdmin(FriendlyAdmin):
    help_list = ("Every gift received, online or recorded by hand (for example cash). Once a gift exists its amount, fund and payment "
                 "references are locked, because giving records are financial evidence. You may correct the donor's details "
                 "and the status (for example Refunded).")
    help_form = ("To record an offline gift, choose the fund and amount and set Provider to 'manual' and Status to 'Succeeded'. "
                 "Saved gifts cannot have their amount changed.")
    list_display = ("reference", "fund", "amount", "currency", "donor_name", "provider", "status", "created_at")
    list_filter = ("status", "provider", "fund")
    search_fields = ("reference", "donor_email", "donor_name", "provider_reference")
    date_hierarchy = "created_at"

    def get_readonly_fields(self, request, obj=None):
        if obj is None:
            return ("reference", "created_at", "updated_at")
        return ("reference", "fund", "user", "amount", "currency", "provider", "provider_reference",
                "metadata", "created_at", "updated_at")

    def get_changeform_initial_data(self, request):
        return {"provider": "manual", "status": "succeeded"}
