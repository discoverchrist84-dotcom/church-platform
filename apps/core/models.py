from django.db import models

from apps.core.validators import validate_image


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class PublishStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    REVIEW = "review", "In review"
    PUBLISHED = "published", "Published"


class SiteSettings(models.Model):
    """The website's name, logo, banner and contact details, editable by an administrator in the admin.

    There is exactly one row. Anything left blank falls back to the defaults in config/settings/base.py.
    """

    church_name = models.CharField(
        "full church name", max_length=200, blank=True,
        help_text="Shown in the footer and when the app is installed. Leave blank to use the default.",
    )
    brand = models.CharField("short name (top line of the header)", max_length=80, blank=True)
    sub_brand = models.CharField("second line of the header", max_length=80, blank=True)
    short_name = models.CharField("home-screen label", max_length=20, blank=True, help_text="Under the icon on a phone's home screen. Keep it short.")
    tagline = models.CharField("description", max_length=300, blank=True, help_text="One sentence that search engines and link previews show.")
    logo = models.ImageField(upload_to="site/", blank=True, help_text="Square PNG, at least 256×256. Shown in the header and on the home page.", validators=[validate_image])
    welcome_text = models.CharField("home page welcome line", max_length=300, blank=True)

    banner_is_active = models.BooleanField("show the banner", default=False)
    banner_text = models.CharField("banner message", max_length=250, blank=True, help_text="e.g. “Annual convention begins Friday: register now.”")
    banner_link = models.URLField("banner link (optional)", blank=True)

    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=40, blank=True)
    address = models.CharField(max_length=250, blank=True)
    facebook_url = models.URLField("Facebook page", blank=True)
    youtube_url = models.URLField("YouTube channel", blank=True)
    instagram_url = models.URLField("Instagram", blank=True)
    x_url = models.URLField("X (Twitter)", blank=True)
    whatsapp_url = models.URLField("WhatsApp link", blank=True)
    footer_note = models.CharField(max_length=250, blank=True)
    payment_instructions = models.TextField(
        "bank transfer details for book orders", blank=True,
        help_text="Shown to people who choose 'bank transfer' in the bookshop: bank, account name, account number, and what to quote.",
    )

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "website settings"
        verbose_name_plural = "website settings"

    def __str__(self):
        return "Website settings"

    CACHE_KEY = "site-settings-v1"

    def save(self, *args, **kwargs):
        self.pk = 1  # always the same single row
        super().save(*args, **kwargs)
        from django.core.cache import cache

        cache.delete(self.CACHE_KEY)

    def delete(self, *args, **kwargs):  # the settings row cannot be deleted, only edited
        return (0, {})

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class StoredFile(models.Model):
    """An uploaded file kept in the database (used when the host's disk is wiped on every restart,
    e.g. Render's free plan). See apps/core/storage.py and the MEDIA_STORAGE setting."""

    name = models.CharField(max_length=500, unique=True)
    content = models.BinaryField()
    size = models.PositiveBigIntegerField(default=0)
    content_type = models.CharField(max_length=100, blank=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "stored upload"

    def __str__(self):
        return self.name
