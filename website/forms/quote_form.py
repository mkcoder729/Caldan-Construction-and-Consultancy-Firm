import re
from django import forms
from django.core.exceptions import ValidationError
from services.models import Service
from ..models.quote import QuoteRequest


class QuoteForm(forms.ModelForm):
    """
    Quote request form for the public website.

    Validates Kenyan phone numbers and ensures all required fields are filled.
    Project type is dynamically populated from the Service model.
    """

    class Meta:
        model = QuoteRequest
        fields = [
            "name", "email", "phone",
            "project_type", "budget_range", "timeline", "details",
            "schedule_call_requested", "preferred_call_time",
        ]
        widgets = {
            "name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Your full name",
                "required": True,
            }),
            "email": forms.EmailInput(attrs={
                "class": "form-control",
                "placeholder": "you@example.com",
                "required": True,
            }),
            "phone": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "07XX XXX XXX",
                "required": True,
            }),
            "project_type": forms.Select(attrs={
                "class": "form-select",
                "required": True,
            }),
            "budget_range": forms.Select(attrs={
                "class": "form-select",
                "required": True,
            }),
            "timeline": forms.Select(attrs={
                "class": "form-select",
                "required": True,
            }),
            "details": forms.Textarea(attrs={
                "class": "form-control",
                "placeholder": "Describe your project in detail...",
                "rows": 6,
                "required": True,
            }),
            # Schedule a call (optional block at the bottom of the form)
            "schedule_call_requested": forms.CheckboxInput(attrs={
                "class": "form-check-input",
                "id": "id_schedule_call_requested",
            }),
            "preferred_call_time": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "e.g. Mon–Fri 9am–12pm",
            }),
        }

    def __init__(self, *args, **kwargs):
        """Populate project_type choices from Service model."""
        super().__init__(*args, **kwargs)

        # Get active services for project type choices
        services = Service.objects.filter(is_active=True).order_by("display_order", "name")
        choices = [(s.category, s.name) for s in services]

        # Add a placeholder option
        choices = [("", "Select project type...")] + list(dict.fromkeys(choices))

        self.fields["project_type"].choices = choices

    def clean_phone(self) -> str:
        """Validate Kenyan phone number format."""
        phone = self.cleaned_data.get("phone", "").strip()

        if not phone:
            raise ValidationError("Phone number is required.")

        # Remove spaces, dashes, parentheses
        cleaned = re.sub(r"[^\d+]", "", phone)

        # Kenyan phone number patterns
        patterns = [
            r"^07\d{8}$",           # 0712345678
            r"^01\d{8}$",           # 0112345678
            r"^2547\d{8}$",         # 254712345678
            r"^2541\d{8}$",         # 254112345678
            r"^\+2547\d{8}$",       # +254712345678
            r"^\+2541\d{8}$",       # +254112345678
            r"^7\d{8}$",            # 712345678
            r"^1\d{8}$",            # 112345678
        ]

        if not any(re.match(pattern, cleaned) for pattern in patterns):
            raise ValidationError(
                "Please enter a valid Kenyan phone number (e.g., 0712345678 or +254712345678)."
            )

        return cleaned

    def clean_details(self) -> str:
        """Ensure project details have minimum length."""
        details = self.cleaned_data.get("details", "").strip()

        if len(details) < 20:
            raise ValidationError("Please provide more details about your project (at least 20 characters).")

        return details

    def clean(self):
        """If schedule_call is requested, require preferred_call_time."""
        cleaned = super().clean()
        if cleaned.get("schedule_call_requested"):
            window = (cleaned.get("preferred_call_time") or "").strip()
            if not window:
                self.add_error(
                    "preferred_call_time",
                    "Please let us know when you're free for the call.",
                )
        return cleaned