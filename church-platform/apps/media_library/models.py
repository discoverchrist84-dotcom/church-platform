from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel


class MediaAsset(TimeStampedModel):
    class Kind(models.TextChoices):
        AUDIO = "audio", "Audio"
        VIDEO = "video", "Video"
        IMAGE = "image", "Image"
        DOCUMENT = "document", "Document"

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="media_assets")
    branch = models.ForeignKey("churches.Branch", null=True, blank=True, on_delete=models.SET_NULL, related_name="media_assets")
    file = models.FileField(upload_to="media/%Y/%m/")
    kind = models.CharField(max_length=10, choices=Kind.choices)
    original_name = models.CharField(max_length=255)
    content_type = models.CharField(max_length=100, blank=True)
    size = models.PositiveBigIntegerField(default=0)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.original_name


class Sermon(TimeStampedModel):
    branch = models.ForeignKey("churches.Branch", on_delete=models.CASCADE, related_name="sermons")
    title = models.CharField(max_length=200)
    speaker = models.CharField(max_length=160, blank=True)
    preached_on = models.DateField()
    description = models.TextField(blank=True)
    scripture = models.CharField(max_length=160, blank=True, help_text="e.g. John 3:16-21")
    asset = models.ForeignKey(MediaAsset, null=True, blank=True, on_delete=models.SET_NULL, related_name="sermons")
    video_url = models.URLField(blank=True, help_text="Optional external link (YouTube, Vimeo...).")
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ["-preached_on"]

    def __str__(self):
        return self.title
