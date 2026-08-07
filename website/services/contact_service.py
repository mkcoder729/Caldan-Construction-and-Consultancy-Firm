import logging
from datetime import timedelta
from django.conf import settings
from django.db.models import Q
from django.template.loader import render_to_string
from django.utils import timezone

from accounts.services.audit_service import AuditService
from ..models.contact import ContactSubmission

logger = logging.getLogger(__name__)


class ContactService:
    """
    Service for handling contact form submissions.

    Handles:
    - Creating ContactSubmission records
    - Sending admin notification emails via Resend
    - Graceful failure handling (email errors don't break user flow)
    """

    @classmethod
    def create_submission(
        cls,
        name: str,
        email: str,
        phone: str,
        subject: str,
        message: str,
        request=None
    ) -> ContactSubmission:
        """
        Create a contact submission and notify admin.

        Args:
            name: Full name of the sender
            email: Email address of the sender
            phone: Phone number of the sender
            subject: Message subject
            message: Message body
            request: HTTP request object (for IP logging, optional)

        Returns:
            ContactSubmission: The created submission object
        """
        # Create the submission
        submission = ContactSubmission.objects.create(
            name=name.strip(),
            email=email.strip().lower(),
            phone=phone.strip(),
            subject=subject.strip(),
            message=message.strip(),
        )

        logger.info(f"Contact submission created: {submission.id} - {email}")

        # Send admin notification (failures don't break the flow)
        try:
            cls._send_admin_notification(submission, request)
        except Exception as e:
            logger.exception(f"Failed to send admin notification for contact {submission.id}: {str(e)}")

        # Auto-reply to the sender (so they know we got the message)
        try:
            cls._send_user_confirmation(submission, request)
        except Exception as e:
            logger.exception(f"Failed to send user confirmation for contact {submission.id}: {str(e)}")

        # In-app notification for every admin (bell icon)
        try:
            cls._notify_admins(submission)
        except Exception as e:
            logger.exception(f"Failed to create in-app notification for contact {submission.id}: {str(e)}")

        return submission

    @classmethod
    def _send_user_confirmation(cls, submission, request=None) -> None:
        """Send a friendly confirmation email to the person who filled out
        the contact form, so they know the message reached us. Best-effort:
        a failure here does not break the flow for the sender."""
        try:
            from notifications.services.email_service import EmailService
            ok = EmailService.send_template(
                to_email=submission.email,
                subject="We received your message — Caldan Construction and Consultancy Firm",
                template_name='email/contact_user_reply.html',
                context={
                    'name': submission.name,
                    'subject': submission.subject,
                    'message': submission.message,
                },
                email_type='CONTACT_USER_REPLY',
            )
            if not ok:
                logger.warning(
                    "Contact user confirmation send returned False for submission %s",
                    submission.id,
                )
        except Exception as exc:
            logger.warning("Contact user confirmation failed for %s: %s", submission.id, exc)

    @classmethod
    def _notify_admins(cls, submission) -> None:
        """Create in-app Notification rows for every admin so the bell
        badge lights up alongside the admin email."""
        try:
            from notifications.services.notification_service import NotificationService
            from notifications.services.router_service import NotificationRouter
            from accounts.models.user import User

            admins = User.objects.filter(is_active=True).filter(
                # chief or superuser, then any platform admin
                is_chief=True
            ) | User.objects.filter(is_active=True, is_superuser=True)
            admins = list(admins.distinct().order_by('-date_joined'))
            if not admins:
                admins = list(User.objects.filter(
                    role=User.Role.PLATFORM_ADMIN, is_active=True
                ).order_by('-date_joined'))

            title = f"📨 New contact message — {submission.subject}"
            message = (
                f"{submission.name} ({submission.email}) sent: "
                f"{submission.message[:140]}"
            )
            for admin in admins:
                try:
                    NotificationRouter.route(
                        user=admin,
                        title=title,
                        message=message,
                        notification_type='SYSTEM',
                        priority='MEDIUM',
                        icon='fa-envelope',
                        action_url=f"/dashboard/contact/{submission.id}/",
                        send_email=False,  # admin email already sent above
                        send_sms=False,
                        metadata={
                            'submission_id': submission.id,
                            'name': submission.name,
                            'email': submission.email,
                            'subject': submission.subject,
                        },
                    )
                except Exception:
                    logger.exception("Contact notification for admin %s failed", admin)
        except Exception as exc:
            logger.warning("Contact admin notification fan-out failed: %s", exc)

    @classmethod
    def _send_admin_notification(cls, submission: ContactSubmission, request=None) -> None:
        """
        Send admin notification email via Resend.

        Delegates to EmailService.send_admin_contact_alert, which:
          - looks up the admin user from the User model (falls back to ADMIN_EMAIL)
          - renders templates/email/contact_received.html
          - logs the attempt to EmailLog
        """
        try:
            from notifications.services.email_service import EmailService

            sent = EmailService.send_admin_contact_alert(
                name=submission.name,
                email=submission.email,
                phone=submission.phone,
                message=submission.message,
            )

            if sent:
                logger.info(f"Contact notification sent to admin for submission: {submission.id}")
            else:
                logger.warning(
                    f"Contact notification reported failure (no admin user or send failed) "
                    f"for submission: {submission.id}"
                )

        except ImportError:
            # Fallback: Resend direct (if notifications app doesn't exist yet)
            logger.warning("EmailService not found, using fallback email sending")
            cls._send_fallback_email(submission)

        except Exception as e:
            logger.exception(f"Email sending failed for contact {submission.id}: {str(e)}")
            raise

    @classmethod
    def _send_fallback_email(cls, submission: ContactSubmission) -> None:
        """
        Fallback email sending using Resend directly.

        Used if the notifications app's EmailService is not available.
        """
        import resend

        resend.api_key = getattr(settings, "RESEND_API_KEY", "")

        if not resend.api_key:
            logger.warning("No RESEND_API_KEY configured, skipping email")
            return

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

        logger.info(f"Fallback contact notification sent to: {admin_email}")

    # ============================================================
    # ADMIN-SIDE METHODS
    # ============================================================

    @classmethod
    def get_admin_messages(cls, user=None, search=None, replied=None):
        """
        Get contact submissions for admin view with optional filters.

        Returns:
            QuerySet[ContactSubmission]
        """
        qs = ContactSubmission.objects.all().order_by("-created_at")

        if search:
            qs = qs.filter(
                Q(name__icontains=search) |
                Q(email__icontains=search) |
                Q(phone__icontains=search) |
                Q(subject__icontains=search) |
                Q(message__icontains=search)
            )
        if replied is not None:
            qs = qs.filter(is_replied=replied)

        if user:
            AuditService.log_action(
                user=user,
                action="CONTACT_MESSAGES_VIEWED",
                entity_type="ContactSubmission",
                details={"filters": {
                    "search": bool(search),
                    "replied": replied,
                }},
            )

        return qs

    @classmethod
    def get_message_by_id(cls, message_id, user=None):
        """Get a single contact submission by ID for admin view."""
        try:
            submission = ContactSubmission.objects.get(id=message_id)
            if user:
                AuditService.log_action(
                    user=user,
                    action="CONTACT_MESSAGE_VIEWED",
                    entity_type="ContactSubmission",
                    entity_id=submission.id,
                    details={"name": submission.name, "email": submission.email},
                )
            return submission
        except ContactSubmission.DoesNotExist:
            return None

    @classmethod
    def delete_message(cls, user, submission):
        """Delete a contact submission. Logs audit."""
        snapshot = {
            "id": submission.id,
            "name": submission.name,
            "email": submission.email,
            "subject": submission.subject,
            "created_at": submission.created_at.isoformat(),
        }
        submission.delete()
        AuditService.log_action(
            user=user,
            action="CONTACT_MESSAGE_DELETED",
            entity_type="ContactSubmission",
            entity_id=snapshot["id"],
            details=snapshot,
        )
        logger.info(f"Contact message deleted: {snapshot['id']} by {user.email}")
        return True

    @classmethod
    def mark_replied(cls, user, submission, replied=True):
        """Toggle replied flag on a contact submission."""
        if replied:
            submission.mark_replied()
        else:
            submission.is_replied = False
            submission.replied_at = None
            submission.save(update_fields=["is_replied", "replied_at"])

        AuditService.log_action(
            user=user,
            action="CONTACT_MESSAGE_MARKED_REPLIED" if replied else "CONTACT_MESSAGE_MARKED_UNREPLIED",
            entity_type="ContactSubmission",
            entity_id=submission.id,
            details={"name": submission.name, "is_replied": submission.is_replied},
        )
        logger.info(f"Contact {submission.id} marked replied={replied} by {user.email}")
        return submission

    @classmethod
    def get_message_stats(cls):
        """Aggregate stats for the dashboard contact list."""
        qs = ContactSubmission.objects.all()
        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_ago = now - timedelta(days=7)

        return {
            "total": qs.count(),
            "unreplied": qs.filter(is_replied=False).count(),
            "replied": qs.filter(is_replied=True).count(),
            "today": qs.filter(created_at__gte=today_start).count(),
            "this_week": qs.filter(created_at__gte=week_ago).count(),
        }