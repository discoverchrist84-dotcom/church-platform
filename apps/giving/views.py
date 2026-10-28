import uuid

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .forms import GiveForm
from .models import Donation, Fund
from .providers import WebhookResult
from .services import ProviderUnavailable, apply_result, queue_receipt, start_checkout

PRESETS = getattr(settings, "GIVING_PRESETS", (10, 25, 50, 100))


def _test_mode():
    return settings.DEBUG and settings.PAYMENT_PROVIDER == "dummy"


def give(request):
    funds = Fund.objects.filter(is_active=True).select_related("branch")

    initial = {}
    fund_slug, branch_slug = request.GET.get("fund"), request.GET.get("branch")
    preselected = None
    if fund_slug:
        preselected = funds.filter(slug=fund_slug).first()
    elif branch_slug:
        preselected = funds.filter(branch__slug=branch_slug).first()
    if preselected:
        initial["fund"] = preselected.pk
    if request.user.is_authenticated:
        initial["donor_name"] = request.user.get_full_name()
        initial["donor_email"] = request.user.email

    form = GiveForm(request.POST or None, funds=funds, initial=initial)
    if request.method == "POST" and form.is_valid():
        cd = form.cleaned_data
        try:
            _, checkout = start_checkout(
                request,
                fund=cd["fund"],
                amount=cd["amount"],
                currency=settings.DEFAULT_CURRENCY,
                donor_name=cd["donor_name"],
                donor_email=cd["donor_email"],
            )
        except ProviderUnavailable:
            messages.error(request, "Online giving isn't switched on yet. Please try again later.")
        else:
            return redirect(checkout.url)

    return render(
        request,
        "giving/give.html",
        {
            "form": form,
            "presets": PRESETS,
            "currency": settings.DEFAULT_CURRENCY,
            "has_funds": funds.exists(),
            "test_mode": _test_mode(),
        },
    )


def thanks(request):
    donation = None
    try:
        ref = uuid.UUID(request.GET.get("ref", ""))
        donation = Donation.objects.select_related("fund").filter(reference=ref).first()
    except ValueError:
        pass
    return render(request, "giving/thanks.html", {"donation": donation})


@login_required
def history(request):
    donations = request.user.donations.select_related("fund")[:100]
    return render(request, "giving/history.html", {"donations": donations})


def dev_pay(request, reference):
    """Stand-in for a payment page while PAYMENT_PROVIDER=dummy (development only)."""
    if not _test_mode():
        raise Http404
    donation = get_object_or_404(Donation.objects.select_related("fund"), reference=reference)
    if request.method == "POST":
        result = WebhookResult(donation_reference=str(donation.reference), status=Donation.Status.SUCCEEDED)
        donation, changed = apply_result(result)
        if changed:
            queue_receipt(donation)
        return redirect(f"{reverse('giving:thanks')}?ref={donation.reference}")
    return render(request, "giving/dev_pay.html", {"donation": donation})
