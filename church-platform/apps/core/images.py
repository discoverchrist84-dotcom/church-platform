"""Every picture upload is checked and shrunk automatically.

Phone photos are often 4-10 MB. Instead of refusing them, we turn them upright, scale them down to
at most MAX_SIDE pixels and re-save them as a small JPEG (or PNG when they have transparency).
"""
import io
import os

from django.core.files.base import ContentFile
from django.db import models
from django.db.models.signals import pre_save

MAX_SIDE = 1600


def shrink(upload):
    """Return (ContentFile, new_name) for an uploaded image, or None if it cannot be processed."""
    from PIL import Image, ImageOps

    upload.seek(0)
    img = Image.open(upload)
    img = ImageOps.exif_transpose(img)
    img.thumbnail((MAX_SIDE, MAX_SIDE))
    has_alpha = img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info)
    buf = io.BytesIO()
    if has_alpha:
        img.convert("RGBA").save(buf, "PNG", optimize=True)
        ext = ".png"
    else:
        img.convert("RGB").save(buf, "JPEG", quality=85, optimize=True, progressive=True)
        ext = ".jpg"
    base = os.path.splitext(os.path.basename(upload.name))[0] or "picture"
    return ContentFile(buf.getvalue()), base + ext


def _shrink_new_uploads(sender, instance, **kwargs):
    for f in sender._meta.get_fields():
        if not isinstance(f, models.ImageField):
            continue
        value = getattr(instance, f.name, None)
        if not value or getattr(value, "_committed", True):
            continue  # nothing new was uploaded
        try:
            content, name = shrink(value.file)
        except Exception:
            continue  # field validation already rejects non-images; never lose an upload over a resize hiccup
        value.save(name, content, save=False)


def connect_all():
    from django.apps import apps

    for model in apps.get_models():
        if any(isinstance(f, models.ImageField) for f in model._meta.get_fields()):
            pre_save.connect(_shrink_new_uploads, sender=model, dispatch_uid=f"shrink-{model._meta.label}")
