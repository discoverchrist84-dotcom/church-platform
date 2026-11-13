from django import forms
from django.urls import reverse

from .richtext import clean_html


class RichTextWidget(forms.Textarea):
    """A formatting editor (bold, italics, headings, lists, links, pictures...) for long text."""

    class Media:
        css = {"all": ("css/richtext.css",)}
        js = ("js/richtext.js",)

    def __init__(self, attrs=None):
        super().__init__({"class": "js-rich", "rows": 14, **(attrs or {})})

    def get_context(self, name, value, attrs):
        ctx = super().get_context(name, value, attrs)
        ctx["widget"]["attrs"]["data-upload-url"] = reverse("core:editor_upload")
        return ctx


class RichTextFormField(forms.CharField):
    widget = RichTextWidget

    def clean(self, value):
        value = super().clean(value)
        return clean_html(value) if value else value
