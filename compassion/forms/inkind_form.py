"""InKindDonationForm — food / clothing / medical / other pledges."""

from django import forms

from compassion.forms._mixins import kenyan_phone_clean, make_phone_field


class InKindDonationForm(forms.Form):
    """Form backing the Give Items modal.

    All fields are free-text / choices; we don't try to coerce the
    quantity or date. Admin gets the raw values and arranges pickup /
    delivery through the workflow.
    """

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

    item_type = forms.ChoiceField(
        choices=[
            ("FOOD", "Food"),
            ("CLOTHING", "Clothing"),
            ("MEDICAL", "Medical supplies"),
            ("OTHER", "Other (please describe)"),
        ],
        widget=forms.Select(attrs={"class": "form-select"}),
        label="Type of item",
        initial="FOOD",
    )

    item_description = forms.CharField(
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "e.g., maize flour, baby clothes, bandages",
        }),
        label="Brief description",
    )

    quantity_estimate = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "e.g., 20kg, 50 items, 2 bags",
        }),
        label="Quantity (approximate)",
    )

    delivery_mode = forms.ChoiceField(
        required=False,
        choices=[
            ("", "Select an option"),
            ("PICKUP", "You'll pick it up"),
            ("DROPOFF", "We'll drop it off"),
            ("ARRANGE", "Let's arrange together"),
        ],
        widget=forms.Select(attrs={"class": "form-select"}),
        label="Delivery / pickup",
        initial="ARRANGE",
    )

    preferred_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            "class": "form-control",
            "type": "date",
        }),
        label="Preferred date (optional)",
    )

    address = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            "class": "form-control",
            "rows": 2,
            "placeholder": "Pickup or drop-off address (if applicable)",
        }),
        label="Address (optional)",
    )

    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            "class": "form-control",
            "rows": 3,
            "placeholder": "Anything else we should know?",
        }),
        label="Additional notes (optional)",
    )

    phone = make_phone_field()

    def clean_phone(self):
        return kenyan_phone_clean(self)