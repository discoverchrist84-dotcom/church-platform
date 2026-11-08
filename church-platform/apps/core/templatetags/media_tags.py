from django import template

register = template.Library()


@register.filter
def file_url(field):
    """URL of an uploaded file, or "" when nothing was uploaded or the file is missing on disk.

    Used as {% if m.photo|file_url %}<img src="{{ m.photo|file_url }}">{% else %}initials{% endif %}
    so a missing file shows the neat initials badge instead of a broken-image icon."""
    if not field:
        return ""
    try:
        if not field.storage.exists(field.name):
            return ""
        return field.url
    except Exception:  # remote storage hiccup etc.: fall back to the placeholder, never break the page
        return ""
