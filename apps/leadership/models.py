from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils.text import slugify

from apps.core.models import TimeStampedModel

from apps.core.validators import validate_image as _check_photo  # noqa: E402  (big photos are shrunk automatically)


class Council(TimeStampedModel):
    """A governing body, e.g. the General Council. With no branch it is church-wide ("general");
    set a branch (headquarters, an area, a district or a station) for a council of that unit."""

    name = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180, unique=True, blank=True)
    branch = models.ForeignKey(
        "churches.Branch", null=True, blank=True, on_delete=models.CASCADE, related_name="councils",
        help_text="Leave empty for a church-wide (general) council.",
    )
    description = models.TextField(blank=True, help_text="What this council does.")
    cover = models.ImageField(
        "group picture", upload_to="councils/covers/", blank=True, validators=[_check_photo],
        help_text="One picture for the whole council (shown on the Leadership page). Pictures of individual people go on each member below.",
    )
    order = models.PositiveSmallIntegerField(default=0, help_text="Smaller numbers show first.")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "name"]

    def __str__(self):
        return self.name

    @property
    def is_general(self):
        return self.branch_id is None

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name) or "council"
            slug, n = base, 2
            while Council.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug, n = f"{base}-{n}", n + 1
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("leadership:council", args=[self.slug])


class CouncilMember(TimeStampedModel):
    council = models.ForeignKey(Council, on_delete=models.CASCADE, related_name="members")
    name = models.CharField(max_length=160)
    title = models.CharField(max_length=120, blank=True, help_text="Office, e.g. General Overseer, Secretary.")
    photo = models.ImageField(upload_to="councils/members/", blank=True, validators=[_check_photo])
    bio = models.TextField(blank=True)
    term_start = models.PositiveSmallIntegerField("served from (year)", null=True, blank=True)
    term_end = models.PositiveSmallIntegerField("served until (year)", null=True, blank=True)
    is_current = models.BooleanField(default=True, help_text="Untick for past office holders.")
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=32, blank=True)
    show_contact = models.BooleanField(
        default=False, help_text="Show email/phone publicly. Off by default for privacy.",
    )
    order = models.PositiveSmallIntegerField(default=0, help_text="Smaller numbers show first.")

    class Meta:
        ordering = ["order", "name"]

    def __str__(self):
        return f"{self.name} ({self.title})" if self.title else self.name

    @property
    def initials(self):
        parts = [p for p in self.name.replace(".", " ").split() if p[:1].isalpha()]
        return "".join(p[0] for p in (parts[:1] + parts[-1:] if len(parts) > 1 else parts[:1])).upper()

    @property
    def tenure(self):
        if self.term_start and self.term_end:
            return f"{self.term_start}–{self.term_end}"
        if self.term_start:
            return f"since {self.term_start}" if self.is_current else f"from {self.term_start}"
        return ""

    def get_absolute_url(self):
        return reverse("leadership:member", args=[self.council.slug, self.pk])
