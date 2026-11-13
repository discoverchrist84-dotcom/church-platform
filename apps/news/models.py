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
    body = models.TextField(help_text="The full story. Use the toolbar for bold, italics, headings, lists, links and pictures.")
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
        from apps.core.richtext import plain_text

        return plain_text(self.body, 200)

    @property
    def safe_source_url(self):
        return self.source_url if self.source_url.lower().startswith(("http://", "https://")) else ""


class Bulletin(TimeStampedModel):
    """An official notice from the National Headquarters: to the whole church, or to chosen areas,
    districts and stations (it reaches every unit beneath the ones you pick)."""

    class Audience(models.TextChoices):
        ALL = "all", "The whole church"
        CHOSEN = "chosen", "Chosen areas, districts or stations"

    title = models.CharField(max_length=220)
    body = models.TextField(help_text="The notice. Use the toolbar for bold, italics, lists, links and pictures.")
    audience = models.CharField(max_length=6, choices=Audience.choices, default=Audience.ALL)
    units = models.ManyToManyField(
        "churches.Branch", blank=True, related_name="bulletins",
        verbose_name="chosen units", help_text="Only used when the audience is 'Chosen'. Everything beneath a chosen unit receives it too.",
    )
    is_urgent = models.BooleanField(default=False, help_text="Shown first and marked URGENT.")
    is_published = models.BooleanField(default=True)
    published_at = models.DateTimeField(default=timezone.now, help_text="Set a future time to schedule it.")
    send_notification = models.BooleanField(
        "also send a notification to members", default=True,
        help_text="Members signed in on the website get an alert (and a push message if they allowed it).",
    )
    notified_at = models.DateTimeField(null=True, blank=True, editable=False)
    author = models.ForeignKey("accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="+", editable=False)

    class Meta:
        ordering = ["-is_urgent", "-published_at"]
        verbose_name = "HQ announcement"
        verbose_name_plural = "HQ announcements"

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("news:bulletin", args=[self.pk])

    @property
    def excerpt(self):
        from apps.core.richtext import plain_text

        return plain_text(self.body, 220)

    @classmethod
    def visible_to(cls, user):
        """Live bulletins this visitor may read: everyone sees church-wide ones; members also see those
        sent to their own station, district or area."""
        from django.db.models import Q

        qs = cls.objects.filter(is_published=True, published_at__lte=timezone.now())
        if not (user and user.is_authenticated):
            return qs.filter(audience=cls.Audience.ALL)
        from apps.churches.models import Membership

        ids = set()
        for m in Membership.objects.filter(user=user).select_related("branch"):
            ids.add(m.branch_id)
            ids.update(b.pk for b in m.branch.ancestors())
        return qs.filter(Q(audience=cls.Audience.ALL) | Q(audience=cls.Audience.CHOSEN, units__in=ids)).distinct()

    def recipients(self):
        """Active accounts that should be notified."""
        from django.contrib.auth import get_user_model

        User = get_user_model()
        if self.audience == self.Audience.ALL:
            return User.objects.filter(is_active=True)
        from apps.churches.models import Membership

        ids = set()
        for b in self.units.all():
            ids.add(b.pk)
            ids.update(d.pk for d in b.descendants())
        return User.objects.filter(is_active=True, memberships__branch_id__in=ids).distinct()

    def send_notifications(self):
        """Notify the audience once. Safe to call again: it does nothing the second time."""
        if self.notified_at or not self.send_notification or not self.is_published:
            return 0
        from apps.realtime.services import notify_many

        n = notify_many(self.recipients(), ("URGENT: " if self.is_urgent else "") + self.title,
                        self.excerpt, self.get_absolute_url())
        type(self).objects.filter(pk=self.pk).update(notified_at=timezone.now())
        return n
