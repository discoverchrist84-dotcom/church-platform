from decimal import Decimal

from django import forms

from .models import Fund


class FundChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, fund):
        return f"{fund.name} — {fund.branch.name}" if fund.branch_id else fund.name


class GiveForm(forms.Form):
    fund = FundChoiceField(queryset=Fund.objects.none(), empty_label=None, label="Give to")
    amount = forms.DecimalField(
        min_value=Decimal("1.00"),
        max_value=Decimal("1000000"),
        max_digits=12,
        decimal_places=2,
        widget=forms.NumberInput(attrs={"step": "0.01", "inputmode": "decimal", "placeholder": "Other amount"}),
    )
    donor_name = forms.CharField(max_length=160, required=False, label="Your name")
    donor_email = forms.EmailField(
        required=False, label="Email for your receipt", help_text="Optional, but we can only email a receipt if you add one."
    )

    def __init__(self, *args, funds=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["fund"].queryset = funds if funds is not None else Fund.objects.filter(is_active=True)
