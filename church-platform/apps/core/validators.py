from django.conf import settings
from django.core.exceptions import ValidationError


def validate_image(f):
    """Shared check for every picture upload: not too big (Pillow already checks it really is an image)."""
    limit = getattr(settings, "MAX_IMAGE_MB", 25)
    if f and getattr(f, "size", 0) > limit * 1024 * 1024:
        raise ValidationError(f"This picture is larger than {limit} MB. Pictures are resized for you, but this one is too big to upload: please choose a smaller one.")
