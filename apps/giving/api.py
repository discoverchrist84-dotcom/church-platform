from decimal import Decimal
from typing import Annotated

from django.conf import settings
from django.http import Http404
from django.shortcuts import get_object_or_404
from ninja import Router, Schema
from ninja.errors import HttpError
from pydantic import Field

from .models import Donation, Fund
from .providers import WebhookError, WebhookResult, get_provider
from .services import ProviderUnavailable, apply_result, queue_receipt, start_checkout

router = Router()


class FundOut(Schema):
    id: int
    name: str
    slug: str
    description: str
    branch_slug: str | None = None

    @staticmethod
    def resolve_branch_slug(obj):
        return obj.branch.slug if obj.branch_id else None


class DonationIn(Schema):
    fund_slug: str
    amount: Annotated[Decimal, Field(gt=0, max_digits=12, decimal_places=2)]
    currency: str = ""
    donor_name: str = ""
    donor_email: str = ""


class CheckoutOut(Schema):
    reference: str
    checkout_url: str


@router.get("/funds", response=list[FundOut])
def list_funds(request, branch: str | None = None):
    qs = Fund.objects.filter(is_active=True).select_related("branch")
    if branch:
        # a branch's own funds plus church-wide funds
        qs = qs.filter(branch__slug=branch) | qs.filter(branch__isnull=True)
    return qs


@router.post("/donations", response={201: CheckoutOut})
def create_donation(request, payload: DonationIn):
    fund = get_object_or_404(Fund, slug=payload.fund_slug, is_active=True)
    try:
        donation, checkout = start_checkout(
            request,
            fund=fund,
            amount=payload.amount,
            currency=payload.currency or settings.DEFAULT_CURRENCY,
            donor_name=payload.donor_name,
            donor_email=payload.donor_email,
        )
    except ProviderUnavailable:
        raise HttpError(501, "This payment provider is not available yet.")
    return 201, {"reference": str(donation.reference), "checkout_url": checkout.url}


@router.post("/webhooks/{provider_name}", auth=None)
def webhook(request, provider_name: str):
    try:
        provider = get_provider(provider_name)
        result = provider.parse_webhook(request)
    except WebhookError as exc:
        raise HttpError(400, str(exc))
    except (NotImplementedError, RuntimeError):
        raise HttpError(501, "Provider not available.")
    donation, changed = apply_result(result)
    if changed and donation.status == Donation.Status.SUCCEEDED:
        queue_receipt(donation)
    return {"ok": True}


@router.get("/dev/confirm/{reference}", url_name="giving_dev_confirm", auth=None)
def dev_confirm(request, reference: str):
    """Development helper that simulates a successful payment."""
    if not settings.DEBUG or settings.PAYMENT_PROVIDER != "dummy":
        raise Http404()
    donation, changed = apply_result(
        WebhookResult(donation_reference=reference, status=Donation.Status.SUCCEEDED)
    )
    if changed:
        queue_receipt(donation)
    return {"ok": True, "status": donation.status}
