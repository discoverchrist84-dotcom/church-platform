from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail

from .models import Donation


@shared_task
def send_donation_receipt(donation_id: int):
    donation = Donation.objects.select_related("fund").get(pk=donation_id)
    email = donation.donor_email or (donation.user.email if donation.user_id else "")
    if not email or donation.status != Donation.Status.SUCCEEDED:
        return False
    send_mail(
        subject=f"Thank you for your gift to {donation.fund.name}",
        message=(
            f"We received your gift of {donation.amount} {donation.currency} "
            f"to {donation.fund.name}.\nReference: {donation.reference}\n\nThank you."
        ),
        from_email=None,
        recipient_list=[email],
    )
    return True
