"""ScheduleCallForm — for big gifts, partnerships, complex logistics."""

from django import forms

from compassion.forms._mixins import kenyan_phone_clean, make_phone_field


class ScheduleCallForm(forms.Form):
    """Form backing the Schedule a Call modal."""

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

    topic = forms.ChoiceField(
        choices=[
            ("LARGE_DONATION", "Large financial gift"),
            ("PARTNERSHIP", "Partnership / corporate giving"),
            ("INKIND_LOGISTICS", "Coordinating an in-kind gift"),
            ("GENERAL", "General conversation"),
        ],
        widget=forms.Select(attrs={"class": "form-select"}),
        label="What would you like to talk about?",
        initial="LARGE_DONATION",
    )

    preferred_time = forms.CharField(
        max_length=120,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "e.g., weekday mornings, Saturday afternoon",
        }),
        label="Preferred time",
        help_text="When works best for you? We'll confirm a slot by email.",
    )

    message = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            "class": "form-control",
            "rows": 4,
            "placeholder": "Anything you'd like us to know in advance.",
        }),
        label="Message (optional)",
    )

    phone = make_phone_field()

    def clean_phone(self):
        return kenyan_phone_clean(self)