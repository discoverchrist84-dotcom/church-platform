from django.conf import settings
from django.db import models

from apps.core.validators import validate_image

from apps.core.models import TimeStampedModel


class Announcement(TimeStampedModel):
    branch = models.ForeignKey("churches.Branch", on_delete=models.CASCADE, related_name="announcements")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    title = models.CharField(max_length=200)
    body = models.TextField()
    is_pinned = models.BooleanField(default=False)
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ["-is_pinned", "-created_at"]

    def __str__(self):
        return self.title


class Event(TimeStampedModel):
    branch = models.ForeignKey("churches.Branch", on_delete=models.CASCADE, related_name="events")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    location = models.CharField(max_length=255, blank=True)
    starts_at = models.DateTimeField(db_index=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    capacity = models.PositiveIntegerField(null=True, blank=True)
    banner = models.ImageField(upload_to="events/", blank=True, validators=[validate_image])
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")

    class Meta:
        ordering = ["starts_at"]

    def __str__(self):
        return self.title


class EventRSVP(TimeStampedModel):
    class Status(models.TextChoices):
        GOING = "going", "Going"
        MAYBE = "maybe", "Maybe"
        NOT_GOING = "no", "Not going"

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="rsvps")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="rsvps")
    status = models.CharField(max_length=8, choices=Status.choices, default=Status.GOING)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["event", "user"], name="unique_event_user_rsvp")]


class Ministry(TimeStampedModel):
    """A group inside a branch: choir, youth, women's fellowship, small group..."""

    branch = models.ForeignKey("churches.Branch", on_delete=models.CASCADE, related_name="ministries")
    name = models.CharField(max_length=160)
    slug = models.SlugField()
    description = models.TextField(blank=True)
    members = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name="ministries")

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "ministries"
        constraints = [models.UniqueConstraint(fields=["branch", "slug"], name="unique_ministry_slug_per_branch")]

    def __str__(self):
        return f"{self.name} ({self.branch})"


class Post(TimeStampedModel):
    """Community board post inside a branch."""

    branch = models.ForeignKey("churches.Branch", on_delete=models.CASCADE, related_name="posts")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="posts")
    title = models.CharField(max_length=200)
    body = models.TextField()
    is_hidden = models.BooleanField(default=False, help_text="Moderation switch.")

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class Comment(TimeStampedModel):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="comments")
    body = models.TextField()
    is_hidden = models.BooleanField(default=False)

    class Meta:
        ordering = ["created_at"]


class PrayerRequest(TimeStampedModel):
    branch = models.ForeignKey("churches.Branch", on_delete=models.CASCADE, related_name="prayer_requests")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="prayer_requests")
    body = models.TextField()
    is_anonymous = models.BooleanField(default=False)
    is_answered = models.BooleanField(default=False)
    is_hidden = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]


class Report(TimeStampedModel):
    """A member flags a post, comment or prayer request for the branch leaders to review."""

    branch = models.ForeignKey("churches.Branch", on_delete=models.CASCADE, related_name="reports")
    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reports_made")
    post = models.ForeignKey(Post, null=True, blank=True, on_delete=models.CASCADE, related_name="reports")
    comment = models.ForeignKey(Comment, null=True, blank=True, on_delete=models.CASCADE, related_name="reports")
    prayer = models.ForeignKey(PrayerRequest, null=True, blank=True, on_delete=models.CASCADE, related_name="reports")
    reason = models.CharField(max_length=500)
    resolved = models.BooleanField(default=False, db_index=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        ordering = ["resolved", "-created_at"]

    def __str__(self):
        return f"Report on {self.target_kind} #{self.target_pk} ({'resolved' if self.resolved else 'open'})"

    @property
    def target_kind(self):
        if self.post_id:
            return "post"
        if self.comment_id:
            return "comment"
        return "prayer"

    @property
    def target_pk(self):
        return self.post_id or self.comment_id or self.prayer_id

    @property
    def target(self):
        return self.post or self.comment or self.prayer

    @property
    def target_text(self):
        t = self.target
        if t is None:
            return ""
        return getattr(t, "title", "") or getattr(t, "body", "")
