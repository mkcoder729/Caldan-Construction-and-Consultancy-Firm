from django import forms
from website.models.newsletter import NewsletterSubscriber


class NewsletterForm(forms.Form):
    """Newsletter subscription form.

    When the email is already subscribed we still consider the form valid
    and let the view branch on `already_subscribed` — that way the user
    sees a friendly "you're already subscribed" message instead of an
    "invalid email" error.
    """

    email = forms.EmailField(
        max_length=254,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Your email address',
            'required': True,
        })
    )