import uuid

from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel


class Fund(TimeStampedModel):
    """Something people can give to: tithe, building fund, missions..."""

    name = models.CharField(max_length=160)
    slug = models.SlugField(unique=True)
    branch = models.ForeignKey(
        "churches.Branch", null=True, blank=True, on_delete=models.CASCADE, related_name="funds",
        help_text="Leave empty for a church-wide fund.",
    )
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Donation(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"
        REFUNDED = "refunded", "Refunded"

    reference = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    fund = models.ForeignKey(Fund, on_delete=models.PROTECT, related_name="donations")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="donations")
    donor_name = models.CharField(max_length=160, blank=True)
    donor_email = models.EmailField(blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="USD")
    provider = models.CharField(max_length=30)
    provider_reference = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.amount} {self.currency} -> {self.fund} ({self.status})"


class GivingAccount(TimeStampedModel):
    """A bank or mobile-money account the church publishes for gifts. Entered by an administrator;
    nothing is shown on the Give page until at least one account is active."""

    class Kind(models.TextChoices):
        BANK = "bank", "Bank account"
        MOBILE = "mobile", "Mobile money"
        OTHER = "other", "Other"

    title = models.CharField(max_length=160, help_text="What it is for, e.g. 'Tithes & offerings' or 'Building fund'.")
    kind = models.CharField(max_length=8, choices=Kind.choices, default=Kind.BANK)
    fund = models.ForeignKey(Fund, null=True, blank=True, on_delete=models.SET_NULL, related_name="accounts",
                             help_text="Optional: the fund this account is for.")
    bank_name = models.CharField("bank / provider", max_length=120, blank=True)
    account_name = models.CharField(max_length=160, blank=True)
    account_number = models.CharField(max_length=60, blank=True)
    currency = models.CharField(max_length=3, default="NGN")
    country = models.CharField(max_length=80, blank=True, help_text="For example Nigeria, Cameroon, Togo.")
    instructions = models.TextField(blank=True, help_text="Anything the giver should do, e.g. 'Use your name and station as the reference'.")
    is_active = models.BooleanField(default=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "title"]

    def __str__(self):
        return self.title
