"""
Celery tasks for the website app.

Handles asynchronous email sending for contact and quote submissions.
"""

import logging
from celery import shared_task
from django.conf import settings
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


@shared_task
def send_admin_contact_notification(submission_id: int) -> bool:
    """
    Send admin notification email for a contact submission.

    Args:
        submission_id: ID of the ContactSubmission

    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    try:
        from .models.contact import ContactSubmission
        submission = ContactSubmission.objects.get(id=submission_id)

        # Delegate to the EmailService helper, which renders the correct template
        # and logs the attempt. Fall back to direct Resend if EmailService is unavailable.
        try:
            from notifications.services.email_service import EmailService

            sent = EmailService.send_admin_contact_alert(
                name=submission.name,
                email=submission.email,
                phone=submission.phone,
                message=submission.message,
            )

            logger.info(f"Contact notification sent via Celery: {submission_id}")
            return bool(sent)

        except ImportError:
            # Fallback: direct Resend
            import resend
            resend.api_key = getattr(settings, "RESEND_API_KEY", "")

            if not resend.api_key:
                logger.warning("No RESEND_API_KEY configured, skipping email")
                return False

            admin_email = getattr(settings, "ADMIN_EMAIL", "info.caldanconstruction@gmail.com")

            html_content = render_to_string("email/contact_received.html", {
                "name": submission.name,
                "email": submission.email,
                "phone": submission.phone,
                "message": submission.message,
            })

            resend.Emails.send({
                "from": getattr(settings, "DEFAULT_FROM_EMAIL", f"Caldan Construction and Consultancy Firm <{admin_email}>"),
                "to": [admin_email],
                "subject": f"New Contact Form Submission - {submission.name}",
                "html": html_content,
            })

            logger.info(f"Contact notification sent via Celery (fallback): {submission_id}")
            return True

    except Exception as e:
        logger.exception(f"Celery task failed for contact {submission_id}: {str(e)}")
        return False


@shared_task
def send_admin_quote_notification(quote_id: int) -> bool:
    """
    Send admin notification email for a quote request.

    Args:
        quote_id: ID of the QuoteRequest

    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    try:
        from .models.quote import QuoteRequest
        quote = QuoteRequest.objects.get(id=quote_id)

        # Delegate to the EmailService helper, which renders the correct template
        # and logs the attempt. Fall back to direct Resend if EmailService is unavailable.
        try:
            from notifications.services.email_service import EmailService

            sent = EmailService.send_admin_quote_alert(
                name=quote.name,
                email=quote.email,
                phone=quote.phone,
                project_type=quote.get_project_type_display(),
                budget=quote.get_budget_range_display(),
                details=quote.details,
            )

            logger.info(f"Quote notification sent via Celery: {quote_id}")
            return bool(sent)

        except ImportError:
            # Fallback: direct Resend
            import resend
            resend.api_key = getattr(settings, "RESEND_API_KEY", "")

            if not resend.api_key:
                logger.warning("No RESEND_API_KEY configured, skipping email")
                return False

            admin_email = getattr(settings, "ADMIN_EMAIL", "info.caldanconstruction@gmail.com")

            html_content = render_to_string("email/quote_received.html", {
                "name": quote.name,
                "email": quote.email,
                "phone": quote.phone,
                "project_type": quote.get_project_type_display(),
                "budget": quote.get_budget_range_display(),
                "details": quote.details,
            })

            resend.Emails.send({
                "from": getattr(settings, "DEFAULT_FROM_EMAIL", f"Caldan Construction and Consultancy Firm <{admin_email}>"),
                "to": [admin_email],
                "subject": f"New Quote Request - {quote.name} - {quote.get_project_type_display()}",
                "html": html_content,
            })

            logger.info(f"Quote notification sent via Celery (fallback): {quote_id}")
            return True

    except Exception as e:
        logger.exception(f"Celery task failed for quote {quote_id}: {str(e)}")
        return False