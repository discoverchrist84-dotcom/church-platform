from django.contrib.auth.models import AbstractUser
from django.db import models

from apps.core.validators import validate_image


class User(AbstractUser):
    email = models.EmailField("email address", unique=True)
    phone = models.CharField(max_length=32, blank=True)
    avatar = models.ImageField(upload_to="avatars/", blank=True, validators=[validate_image])
    bio = models.TextField(blank=True)
    # A person's primary branch lives on churches.Membership.is_primary
    # (keeps accounts free of a circular dependency on churches).

    def __str__(self):
        return self.get_full_name() or self.username
