"""DonationForm — monetary donation form (powers the Paystack modal)."""

from decimal import Decimal, InvalidOperation

from django import forms

from compassion.forms._mixins import kenyan_phone_clean, make_phone_field


class DonationForm(forms.Form):
    """Form backing the Give Money modal and the /compassion/donate/ page.

    Note: this is intentionally NOT a ModelForm — we want to capture the
    raw form input and let DonationService.create_pending_donation()
    orchestrate DB writes + audit + side effects in one place. The
    Paystack reference is generated server-side at save time, not here.
    """

    QUICK_AMOUNTS = [
        (Decimal("500"), "KSh 500"),
        (Decimal("1000"), "KSh 1,000"),
        (Decimal("2500"), "KSh 2,500"),
        (Decimal("5000"), "KSh 5,000"),
    ]

    name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Your full name",
            "autocomplete": "name",
        }),
        label="Full name",
    )

    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            "class": "form-control",
            "placeholder": "[email protected]",
            "autocomplete": "email",
        }),
        label="Email address",
    )

    amount = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("10.00"),
        widget=forms.NumberInput(attrs={
            "class": "form-control",
            "placeholder": "Amount in KSh",
            "min": "10",
            "step": "10",
            "inputmode": "decimal",
        }),
        label="Amount (KSh)",
    )

    purpose = forms.ChoiceField(
        choices=[
            ("GENERAL", "Where most needed"),
            ("HOSPITAL", "Hospital outreach"),
            ("PRISON", "Prison outreach"),
            ("NEIGHBOURHOOD", "Neighbourhood outreach"),
        ],
        widget=forms.Select(attrs={"class": "form-select"}),
        label="I'd like my gift to support",
        initial="GENERAL",
    )

    note = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            "class": "form-control",
            "rows": 3,
            "placeholder": "Optional note — prayers, dedications, anything you'd like us to know.",
        }),
        label="Note (optional)",
    )

    phone = make_phone_field()

    def clean_amount(self):
        raw = self.cleaned_data.get("amount")
        if raw is None:
            return raw
        try:
            amount = Decimal(str(raw)).quantize(Decimal("0.01"))
        except (InvalidOperation, TypeError, ValueError):
            from django.core.exceptions import ValidationError
            raise ValidationError("Please enter a valid amount.")
        if amount < Decimal("10.00"):
            from django.core.exceptions import ValidationError
            raise ValidationError("Minimum donation is KSh 10.00.")
        return amount

    def clean_phone(self):
        return kenyan_phone_clean(self)