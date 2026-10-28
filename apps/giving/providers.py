"""Payment providers behind one small interface.

Payment support differs by country (Stripe, Paystack, Flutterwave, PayPal...),
so the rest of the app only talks to `PaymentProvider`. To add a gateway,
subclass it, implement the two methods, and register it in `PROVIDERS`.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from django.conf import settings
from django.urls import reverse

from .models import Donation


@dataclass
class Checkout:
    url: str
    provider_reference: str = ""


@dataclass
class WebhookResult:
    donation_reference: str
    status: str  # one of Donation.Status values
    provider_reference: str = ""


class WebhookError(Exception):
    pass


class PaymentProvider(ABC):
    name: str

    @abstractmethod
    def create_checkout(self, donation: Donation, request) -> Checkout:
        """Start a payment and return where to send the donor."""

    @abstractmethod
    def parse_webhook(self, request) -> WebhookResult:
        """Verify the signature and translate the provider payload.

        Must raise WebhookError if verification fails.
        """


class DummyProvider(PaymentProvider):
    """Development only. Confirms instantly through the webhook endpoint."""

    name = "dummy"

    def create_checkout(self, donation, request):
        if not settings.DEBUG:
            raise RuntimeError("The dummy payment provider is disabled when DEBUG is off.")
        return Checkout(
            url=request.build_absolute_uri(reverse("giving:dev_pay", args=[donation.reference])),
            provider_reference=f"dummy_{donation.reference}",
        )

    def parse_webhook(self, request):
        if not settings.DEBUG:
            raise WebhookError("Dummy webhook disabled.")
        import json

        try:
            data = json.loads(request.body or b"{}")
            return WebhookResult(
                donation_reference=data["reference"],
                status=data.get("status", Donation.Status.SUCCEEDED),
                provider_reference=data.get("provider_reference", ""),
            )
        except (ValueError, KeyError) as exc:
            raise WebhookError("Malformed payload.") from exc


class StripeProvider(PaymentProvider):
    """Placeholder. Implement with the `stripe` package (Checkout Sessions +
    signed webhooks) before enabling PAYMENT_PROVIDER=stripe."""

    name = "stripe"

    def create_checkout(self, donation, request):
        raise NotImplementedError("Stripe is not implemented yet.")

    def parse_webhook(self, request):
        raise NotImplementedError("Stripe is not implemented yet.")


PROVIDERS: dict[str, type[PaymentProvider]] = {
    DummyProvider.name: DummyProvider,
    StripeProvider.name: StripeProvider,
}


def get_provider(name: str | None = None) -> PaymentProvider:
    name = name or settings.PAYMENT_PROVIDER
    try:
        return PROVIDERS[name]()
    except KeyError:
        raise RuntimeError(f"Unknown payment provider: {name}")
