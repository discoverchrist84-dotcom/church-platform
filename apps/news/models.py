from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify

from apps.core.models import TimeStampedModel
from apps.core.validators import validate_image


class NewsQuerySet(models.QuerySet):
    def live(self):
        """Published and already due (a future 'publish on' date keeps an article hidden until then)."""
        return self.filter(is_published=True, published_at__lte=timezone.now())


class NewsArticle(TimeStampedModel):
    class Scope(models.TextChoices):
        INSIDE = "inside", "In our church"
        OUTSIDE = "outside", "Outside the church"

    class Topic(models.TextChoices):
        CHURCH = "church", "Church news"
        PROGRAMME = "programme", "Programmes & events"
        TESTIMONY = "testimony", "Testimonies"
        OTHER_CHURCHES = "churches", "Other churches"
        COMMUNITY = "community", "Community & region"
        NATION = "nation", "Nation"
        WORLD = "world", "Around the world"

    title = models.CharField(max_length=220)
    slug = models.SlugField(max_length=240, unique=True, blank=True)
    summary = models.CharField(max_length=300, blank=True, help_text="One or two sentences shown in the news list.")
    body = models.TextField(help_text="The full story. Leave a blank line between paragraphs.")
    image = models.ImageField(upload_to="news/", blank=True, validators=[validate_image], help_text="Optional picture for the story. Large photos are resized automatically.")
    scope = models.CharField(
        max_length=8, choices=Scope.choices, default=Scope.INSIDE,
        help_text="'In our church' for our own news. 'Outside the church' for news from other churches, the community, the nation or the world.",
    )
    topic = models.CharField(max_length=10, choices=Topic.choices, default=Topic.CHURCH)
    branch = models.ForeignKey(
        "churches.Branch", null=True, blank=True, on_delete=models.SET_NULL, related_name="news",
        help_text="Optional: the area, district or station this news is about. Leave empty for church-wide or outside news.",
    )
    place = models.CharField(max_length=120, blank=True, help_text="Optional town, region or country the story is about.")
    author_name = models.CharField(max_length=120, blank=True)
    source_name = models.CharField(max_length=160, blank=True, help_text="For outside news: who reported it, e.g. a newspaper or another church.")
    source_url = models.URLField("source link", blank=True, help_text="Optional link to the original story (must start with http:// or https://).")
    published_at = models.DateTimeField("publish on", default=timezone.now, help_text="The story appears on this date and time. Set a future time to schedule it.")
    is_published = models.BooleanField(default=True, help_text="Untick to keep it as a draft.")
    is_pinned = models.BooleanField("pin to the top", default=False)

    objects = NewsQuerySet.as_manager()

    class Meta:
        ordering = ["-is_pinned", "-published_at"]
        verbose_name = "news story"
        verbose_name_plural = "news stories"

    def __str__(self):
        return self.title

    def clean(self):
        super().clean()
        if self.source_url and not self.source_url.lower().startswith(("http://", "https://")):
            raise ValidationError({"source_url": "The link must start with http:// or https://"})

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title)[:200] or "news"
            slug, n = base, 2
            while NewsArticle.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug, n = f"{base}-{n}", n + 1
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("news:detail", args=[self.slug])

    @property
    def excerpt(self):
        if self.summary:
            return self.summary
        text = " ".join(self.body.split())
        return text[:200] + ("…" if len(text) > 200 else "")

    @property
    def safe_source_url(self):
        return self.source_url if self.source_url.lower().startswith(("http://", "https://")) else ""
