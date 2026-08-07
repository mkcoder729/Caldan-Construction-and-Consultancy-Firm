import re
from django import forms
from django.core.exceptions import ValidationError
from ..models.contact import ContactSubmission


class ContactForm(forms.ModelForm):
    """
    Contact form for the public website.

    Validates Kenyan phone numbers and ensures all required fields are filled.
    """

    class Meta:
        model = ContactSubmission
        fields = ["name", "email", "phone", "subject", "message"]
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
            "subject": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "What's this about?",
                "required": True,
            }),
            "message": forms.Textarea(attrs={
                "class": "form-control",
                "placeholder": "Tell us about your project or inquiry...",
                "rows": 6,
                "required": True,
            }),
        }

    def clean_phone(self) -> str:
        """Validate Kenyan phone number format."""
        phone = self.cleaned_data.get("phone", "").strip()

        if not phone:
            raise ValidationError("Phone number is required.")

        cleaned = re.sub(r"[^\d+]", "", phone)

        patterns = [
            r"^07\d{8}$",
            r"^01\d{8}$",
            r"^2547\d{8}$",
            r"^2541\d{8}$",
            r"^\+2547\d{8}$",
            r"^\+2541\d{8}$",
            r"^7\d{8}$",
            r"^1\d{8}$",
        ]

        if not any(re.match(pattern, cleaned) for pattern in patterns):
            raise ValidationError(
                "Please enter a valid Kenyan phone number (e.g., 0712345678 or +254712345678)."
            )

        return cleaned

    def clean_message(self) -> str:
        """Ensure message has minimum length."""
        message = self.cleaned_data.get("message", "").strip()

        if len(message) < 10:
            raise ValidationError("Message must be at least 10 characters long.")

        return message