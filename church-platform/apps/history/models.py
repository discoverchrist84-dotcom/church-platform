from django.db import models

from apps.core.validators import validate_image
from django.urls import reverse
from django.utils import timezone

from apps.core.models import PublishStatus, TimeStampedModel


def format_year(year: int | None) -> str:
    """Negative years are BC; positive are AD."""
    if year is None:
        return ""
    return f"{abs(year)} BC" if year < 0 else f"AD {year}"


class PublishedQuerySet(models.QuerySet):
    def published(self):
        return self.filter(status=PublishStatus.PUBLISHED)


class Era(TimeStampedModel):
    name = models.CharField(max_length=120)
    slug = models.SlugField(unique=True)
    start_year = models.IntegerField(help_text="Negative for BC, e.g. -4 for 4 BC.")
    end_year = models.IntegerField(null=True, blank=True)
    summary = models.TextField(blank=True)

    class Meta:
        ordering = ["start_year"]

    def __str__(self):
        return self.name

    @property
    def span(self):
        end = format_year(self.end_year) if self.end_year is not None else "present"
        return f"{format_year(self.start_year)} – {end}"


class Tag(models.Model):
    name = models.CharField(max_length=60, unique=True)
    slug = models.SlugField(unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Source(TimeStampedModel):
    """A citation. Every published entry should point at one or more sources."""

    class Kind(models.TextChoices):
        PRIMARY = "primary", "Primary source"
        SECONDARY = "secondary", "Secondary source"

    title = models.CharField(max_length=255)
    author = models.CharField(max_length=160, blank=True)
    publication = models.CharField(max_length=255, blank=True)
    year = models.IntegerField(null=True, blank=True)
    url = models.URLField(blank=True)
    kind = models.CharField(max_length=10, choices=Kind.choices, default=Kind.SECONDARY)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return f"{self.title} ({self.author})" if self.author else self.title


class Place(TimeStampedModel):
    name = models.CharField(max_length=160)
    slug = models.SlugField(unique=True)
    modern_name = models.CharField(max_length=160, blank=True)
    description = models.TextField(blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Figure(TimeStampedModel):
    name = models.CharField(max_length=160)
    slug = models.SlugField(unique=True)
    title = models.CharField(max_length=160, blank=True, help_text="e.g. Bishop of Hippo")
    born_year = models.IntegerField(null=True, blank=True)
    died_year = models.IntegerField(null=True, blank=True)
    bio = models.TextField(blank=True)
    portrait = models.ImageField(upload_to="history/figures/", blank=True, validators=[validate_image])
    sources = models.ManyToManyField(Source, blank=True, related_name="figures")
    status = models.CharField(
        max_length=10, choices=PublishStatus.choices, default=PublishStatus.DRAFT
    )

    objects = PublishedQuerySet.as_manager()

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("history:figure", args=[self.slug])

    @property
    def lifespan(self):
        if self.born_year is None and self.died_year is None:
            return ""
        born = format_year(self.born_year) if self.born_year is not None else "?"
        died = format_year(self.died_year) if self.died_year is not None else "?"
        return f"{born} – {died}"


class HistoricalEvent(TimeStampedModel):
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    era = models.ForeignKey(Era, null=True, blank=True, on_delete=models.SET_NULL, related_name="events")
    year_start = models.IntegerField(db_index=True, help_text="Negative for BC.")
    year_end = models.IntegerField(null=True, blank=True)
    date_display = models.CharField(
        max_length=80, blank=True, help_text='Optional override, e.g. "c. AD 30–33".'
    )
    summary = models.TextField(help_text="One or two sentences shown in lists.")
    body = models.TextField(blank=True, help_text="Full article. Plain text; blank line = paragraph.")
    hero_image = models.ImageField(upload_to="history/events/", blank=True, validators=[validate_image])

    figures = models.ManyToManyField(Figure, blank=True, related_name="events")
    places = models.ManyToManyField(Place, blank=True, related_name="events")
    sources = models.ManyToManyField(Source, blank=True, related_name="events")
    tags = models.ManyToManyField(Tag, blank=True, related_name="events")

    status = models.CharField(
        max_length=10, choices=PublishStatus.choices, default=PublishStatus.DRAFT, db_index=True
    )
    published_at = models.DateTimeField(null=True, blank=True)

    objects = PublishedQuerySet.as_manager()

    class Meta:
        ordering = ["year_start", "title"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if self.status == PublishStatus.PUBLISHED and self.published_at is None:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("history:event", args=[self.slug])

    @property
    def when(self):
        if self.date_display:
            return self.date_display
        start = format_year(self.year_start)
        if self.year_end is not None and self.year_end != self.year_start:
            return f"{start} – {format_year(self.year_end)}"
        return start


class Document(TimeStampedModel):
    """Creeds, council canons, letters and other primary texts."""

    class Kind(models.TextChoices):
        CREED = "creed", "Creed"
        COUNCIL = "council", "Council / canons"
        LETTER = "letter", "Letter"
        TREATISE = "treatise", "Treatise"
        OTHER = "other", "Other"

    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    kind = models.CharField(max_length=10, choices=Kind.choices, default=Kind.OTHER)
    year = models.IntegerField(null=True, blank=True)
    text = models.TextField(blank=True)
    translation_note = models.CharField(max_length=255, blank=True)
    source = models.ForeignKey(
        Source, null=True, blank=True, on_delete=models.SET_NULL, related_name="documents"
    )
    status = models.CharField(
        max_length=10, choices=PublishStatus.choices, default=PublishStatus.DRAFT
    )

    objects = PublishedQuerySet.as_manager()

    class Meta:
        ordering = ["year", "title"]

    def __str__(self):
        return self.title
