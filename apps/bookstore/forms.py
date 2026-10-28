from django import forms

from .models import Order
from .services import online_payments_available


class CheckoutForm(forms.Form):
    name = forms.CharField(label="Full name", max_length=160)
    email = forms.EmailField(help_text="Your receipt and download links go here.")
    phone = forms.CharField(max_length=32, required=False)
    delivery = forms.ChoiceField(choices=Order.Delivery.choices[:2], initial="ship", required=False, widget=forms.RadioSelect)
    address = forms.CharField(label="Street address", max_length=255, required=False)
    city = forms.CharField(max_length=100, required=False)
    state = forms.CharField(label="State / region", max_length=100, required=False)
    country = forms.CharField(max_length=100, required=False)
    payment_method = forms.ChoiceField(choices=[], widget=forms.RadioSelect)
    note = forms.CharField(label="Note to us (optional)", required=False, widget=forms.Textarea(attrs={"rows": 3}))

    def __init__(self, *args, has_print=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.has_print = has_print
        choices = []
        if online_payments_available():
            choices.append((Order.Payment.ONLINE, "Pay online (test mode)"))
        choices.append((Order.Payment.TRANSFER, "Bank transfer: we send you the details"))
        if has_print:
            choices.append((Order.Payment.CASH, "Pay when I receive or collect it"))
        self.fields["payment_method"].choices = choices
        self.fields["payment_method"].initial = choices[0][0]

    def clean(self):
        cd = super().clean()
        if self.has_print:
            if not cd.get("delivery"):
                self.add_error("delivery", "Choose delivery or collection.")
            elif cd["delivery"] == Order.Delivery.SHIP:
                for f in ("address", "city"):
                    if not cd.get(f):
                        self.add_error(f, "We need this to deliver your books.")
        return cd
