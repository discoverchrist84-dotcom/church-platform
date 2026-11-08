"""Donation logic shared by the web pages and the JSON API."""
import logging

from django.db import transaction
from django.http import Http404

from .models import Donation
from .providers import WebhookResult, get_provider
from .tasks import send_donation_receipt

logger = logging.getLogger(__name__)


class ProviderUnavailable(Exception):
    """The configured payment provider can't take payments right now."""


def start_checkout(request, *, fund, amount, currency, donor_name="", donor_email=""):
    """Create a pending donation and ask the provider where to send the donor."""
    user = request.user if request.user.is_authenticated else None
    try:
        provider = get_provider()
    except RuntimeError as exc:
        raise ProviderUnavailable(str(exc)) from exc

    donation = Donation.objects.create(
        fund=fund,
        user=user,
        donor_name=donor_name or (user.get_full_name() if user else ""),
        donor_email=donor_email or (user.email if user else ""),
        amount=amount,
        currency=(currency or "USD").upper()[:3],
        provider=provider.name,
    )
    try:
        checkout = provider.create_checkout(donation, request)
    except (NotImplementedError, RuntimeError) as exc:
        donation.status = Donation.Status.FAILED
        donation.save(update_fields=["status", "updated_at"])
        raise ProviderUnavailable(str(exc)) from exc

    donation.provider_reference = checkout.provider_reference
    donation.save(update_fields=["provider_reference", "updated_at"])
    return donation, checkout


def queue_receipt(donation):
    """Never let a broker outage break payment confirmation."""
    try:
        send_donation_receipt.delay(donation.pk)
    except Exception:  # noqa: BLE001
        logger.exception("Could not queue receipt for donation %s", donation.pk)


def apply_result(result: WebhookResult):
    """Record a provider's verdict. Returns (donation, changed)."""
    with transaction.atomic():
        donation = Donation.objects.select_for_update().filter(reference=result.donation_reference).first()
        if donation is None:
            raise Http404("Unknown donation.")
        # Webhooks can be delivered more than once; never re-process a settled donation.
        if donation.status == Donation.Status.SUCCEEDED and result.status == Donation.Status.SUCCEEDED:
            return donation, False
        donation.status = result.status
        if result.provider_reference:
            donation.provider_reference = result.provider_reference
        donation.save(update_fields=["status", "provider_reference", "updated_at"])
    return donation, True
