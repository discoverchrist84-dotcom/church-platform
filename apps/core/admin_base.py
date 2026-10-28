"""Shared building blocks that make every admin page easier to understand."""
import csv

from django.contrib import admin, messages
from django.contrib.admin.utils import label_for_field, lookup_field
from django.http import HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import ngettext


def _safe_cell(value):
    """Stop spreadsheets from running text such as =HYPERLINK(...) that a member may have typed."""
    text = "" if value is None else str(value)
    return "'" + text if text[:1] in ("=", "+", "-", "@", "\t", "\r") else text


class ExportCsvMixin:
    """Adds “Download selected as a spreadsheet (CSV)” to the Action menu of any list."""

    @admin.action(description="Download selected as a spreadsheet (CSV)")
    def export_csv(self, request, queryset):
        columns = [c for c in self.get_list_display(request) if c not in ("action_checkbox", "thumb")]
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        stamp = timezone.localtime().strftime("%Y-%m-%d")
        response["Content-Disposition"] = f'attachment; filename="{self.model._meta.model_name}-{stamp}.csv"'
        response.write("\ufeff")  # so Excel opens accents and non-English names correctly
        writer = csv.writer(response)
        writer.writerow([str(label_for_field(c, self.model, self)) for c in columns])
        for obj in queryset:
            row = []
            for c in columns:
                try:
                    _, _, value = lookup_field(c, obj, self)
                    field = self.model._meta.get_field(c) if c in {f.name for f in self.model._meta.fields} else None
                    if field is not None and field.choices:
                        value = getattr(obj, f"get_{c}_display")()  # "Area", not the stored code "region"
                except Exception:  # a broken column must not break the whole download
                    value = ""
                row.append(_safe_cell(value))
            writer.writerow(row)
        return response

    def get_actions(self, request):
        actions = super().get_actions(request)
        if self.has_view_permission(request) and "export_csv" not in actions:
            action = self.get_action("export_csv")
            if action:
                actions[action[1]] = action
        return actions


class FriendlyAdmin(ExportCsvMixin, admin.ModelAdmin):
    """Adds a plain-English help box above the list and the form, and sensible defaults.

    Set ``help_list`` / ``help_form`` (short sentences) on each admin class.
    """

    help_list = ""
    help_form = ""
    save_on_top = True          # Save buttons at the top as well, so long forms are easy to finish
    list_per_page = 25
    empty_value_display = "—"
    change_list_template = "admin/church/change_list.html"
    change_form_template = "admin/church/change_form.html"

    def changelist_view(self, request, extra_context=None):
        extra = {"admin_help": self.help_list, "model_label": self.model._meta.verbose_name_plural}
        return super().changelist_view(request, {**extra, **(extra_context or {})})

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        extra = {"admin_help": self.help_form, "model_label": self.model._meta.verbose_name}
        return super().changeform_view(request, object_id, form_url, {**extra, **(extra_context or {})})


def _note(modeladmin, request, count, template_one, template_many):
    modeladmin.message_user(
        request, ngettext(template_one, template_many, count) % {"n": count}, messages.SUCCESS
    )


def flag_action(field, value, description, one, many):
    """Build a bulk action that sets a True/False field on the selected rows."""

    @admin.action(description=description, permissions=["change"])
    def action(modeladmin, request, queryset):
        # save() each row (not queryset.update) so models that react to saving still do.
        n = 0
        for obj in queryset:
            if getattr(obj, field) != value:
                setattr(obj, field, value)
                obj.save()
                n += 1
        _note(modeladmin, request, n, one, many)

    action.__name__ = f"set_{field}_{str(value).lower()}"
    return action


class SingletonAdmin(FriendlyAdmin):
    """For settings that exist exactly once: the list page jumps straight to the one form."""

    actions = None

    def has_add_permission(self, request):
        return not self.model.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        obj = self.model.load()
        return redirect(reverse(f"{self.admin_site.name}:{self.model._meta.app_label}_{self.model._meta.model_name}_change", args=[obj.pk]))

    def get_actions(self, request):
        return {}


def picture_preview(obj, field):
    """Small preview of an uploaded picture for admin forms, so you can see it saved and where it is stored."""
    from django.utils.html import format_html

    f = getattr(obj, field, None) if obj and obj.pk else None
    if not f:
        return "No picture saved yet. Choose a file, check the preview, then press Save."
    try:
        if not f.storage.exists(f.name):
            return format_html("⚠️ The file {} was saved in the database but is missing on disk. Upload it again.", f.name)
        return format_html('<img class="apreview" src="{}" alt=""><small>{}</small>', f.url, f.name)
    except Exception:
        return "The picture could not be read. Upload it again."
