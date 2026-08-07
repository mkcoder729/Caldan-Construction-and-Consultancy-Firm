import logging
from datetime import timedelta
from django.conf import settings
from django.db.models import Q
from django.template.loader import render_to_string
from django.utils import timezone

from accounts.services.audit_service import AuditService
from ..models.quote import QuoteRequest

logger = logging.getLogger(__name__)


class QuoteService:
    """
    Service for handling quote request submissions.

    Handles:
    - Creating QuoteRequest records
    - Sending admin notification emails via Resend
    - Graceful failure handling (email errors don't break user flow)
    """

    @classmethod
    def create_quote(
        cls,
        name: str,
        email: str,
        phone: str,
        project_type: str,
        budget_range: str,
        timeline: str,
        details: str,
        schedule_call_requested: bool = False,
        preferred_call_time: str = "",
        request=None
    ) -> QuoteRequest:
        """
        Create a quote request and notify admin.

        Args:
            name: Full name of the requester
            email: Email address of the requester
            phone: Phone number of the requester
            project_type: Type of project (from Service.Category)
            budget_range: Budget range selection
            timeline: Timeline selection
            details: Project details description
            schedule_call_requested: True if the requester wants a callback
            preferred_call_time: Free-text window when they're free
            request: HTTP request object (for IP logging, optional)

        Returns:
            QuoteRequest: The created quote request object
        """
        # Create the quote request
        quote = QuoteRequest.objects.create(
            name=name.strip(),
            email=email.strip().lower(),
            phone=phone.strip(),
            project_type=project_type,
            budget_range=budget_range,
            timeline=timeline,
            details=details.strip(),
            schedule_call_requested=bool(schedule_call_requested),
            preferred_call_time=(preferred_call_time or "").strip(),
        )

        logger.info(f"Quote request created: {quote.id} - {email} - {project_type}")

        # Send admin notification (failures don't break the flow)
        try:
            cls._send_admin_notification(quote, request)
        except Exception as e:
            logger.exception(f"Failed to send admin notification for quote {quote.id}: {str(e)}")

        # Auto-reply to the requester (so they know we got the quote request)
        try:
            cls._send_user_confirmation(quote, request)
        except Exception as e:
            logger.exception(f"Failed to send user confirmation for quote {quote.id}: {str(e)}")

        # If a schedule-call request was attached, also notify admins of that
        if quote.schedule_call_requested:
            try:
                cls._notify_admins_schedule_call(quote)
            except Exception:
                logger.exception("schedule-call admin notify failed for quote %s", quote.id)

        # In-app notification for every admin (bell icon)
        try:
            cls._notify_admins(quote)
        except Exception as e:
            logger.exception(f"Failed to create in-app notification for quote {quote.id}: {str(e)}")

        return quote

    @classmethod
    def _send_user_confirmation(cls, quote, request=None) -> None:
        """Friendly auto-reply so the requester knows we received their quote."""
        try:
            from notifications.services.email_service import EmailService
            ok = EmailService.send_template(
                to_email=quote.email,
                subject="We received your quote request — Caldan Construction and Consultancy Firm",
                template_name='email/quote_user_reply.html',
                context={
                    'name': quote.name,
                    'project_type': quote.get_project_type_display(),
                    'timeline': quote.get_timeline_display(),
                    'details': quote.details,
                    'schedule_call': quote.schedule_call_requested,
                    'preferred_call_time': quote.preferred_call_time or '',
                },
                email_type='QUOTE_USER_REPLY',
            )
            if not ok:
                logger.warning("Quote user confirmation send returned False for quote %s", quote.id)
        except Exception as exc:
            logger.warning("Quote user confirmation failed for %s: %s", quote.id, exc)

    @classmethod
    def _notify_admins(cls, quote) -> None:
        """In-app Notification for every admin (bell) for a new quote."""
        try:
            from notifications.services.router_service import NotificationRouter
            from accounts.models.user import User

            admins_qs = User.objects.filter(is_active=True).filter(
                is_chief=True
            ) | User.objects.filter(is_active=True, is_superuser=True)
            admins = list(admins_qs.distinct().order_by('-date_joined'))
            if not admins:
                admins = list(User.objects.filter(
                    role=User.Role.PLATFORM_ADMIN, is_active=True
                ).order_by('-date_joined'))

            title = f"📋 New quote request — {quote.name}"
            message = (
                f"{quote.name} ({quote.email}) requested a quote for "
                f"{quote.get_project_type_display()} (timeline: {quote.get_timeline_display()})."
            )
            action_url = f"/dashboard/quotes/{quote.id}/"
            for admin in admins:
                try:
                    NotificationRouter.route(
                        user=admin,
                        title=title,
                        message=message,
                        notification_type='SYSTEM',
                        priority='HIGH' if quote.schedule_call_requested else 'MEDIUM',
                        icon='fa-file-invoice-dollar',
                        action_url=action_url,
                        send_email=False,
                        send_sms=False,
                        metadata={
                            'quote_id': quote.id,
                            'project_type': quote.project_type,
                            'budget_range': quote.budget_range,
                            'timeline': quote.timeline,
                            'schedule_call': quote.schedule_call_requested,
                        },
                    )
                except Exception:
                    logger.exception("Quote notification for admin %s failed", admin)
        except Exception as exc:
            logger.warning("Quote admin notification fan-out failed: %s", exc)

    @classmethod
    def _notify_admins_schedule_call(cls, quote) -> None:
        """High-priority ping when the requester wants a callback.

        Two channels are used, with intentional separation of concerns:

        * **Email** — single email to the shared ``ADMIN_EMAIL`` inbox. The
          admin inbox is the canonical source of truth for all admin-facing
          email (orders, payments, audit, low-stock, milestone overdue, etc.),
          so schedule-call alerts route there too rather than each admin's
          personal address.
        * **In-app bell** — every chief/superuser/platform-admin gets a
          personal URGENT badge via ``NotificationRouter.route()`` so the
          dashboard shows them immediately.
        """
        admin_email = (
            getattr(settings, 'ADMIN_EMAIL', '')
            or 'info.caldanconstruction@gmail.com'
        )
        title = f"📞 Schedule a call — {quote.name}"
        message = (
            f"{quote.name} requested a call. Preferred time: "
            f"{quote.preferred_call_time or 'anytime'}. Phone: {quote.phone}."
        )
        dashboard_url = f"/dashboard/quotes/{quote.id}/"

        # 1. Single email to the shared admin inbox (uses new dedicated template)
        try:
            from notifications.services.email_service import EmailService
            EmailService.send_template(
                to_email=admin_email,
                subject=f"📞 Schedule a call — {quote.name}",
                template_name='email/schedule_call_requested.html',
                context={
                    'name': quote.name,
                    'phone': quote.phone,
                    'email': quote.email,
                    'preferred_call_time': quote.preferred_call_time or 'Any time',
                    'project_type': quote.get_project_type_display(),
                    'budget_range': quote.get_budget_range_display(),
                    'timeline': quote.get_timeline_display(),
                    'details': quote.details,
                    'quote_id': quote.id,
                    'submitted_at': quote.created_at,
                    'title': title,
                    'message': message,
                    'action_url': dashboard_url,
                    'cta_label': 'Open Quote in Dashboard',
                },
                email_type='SCHEDULE_CALL_REQUESTED',
            )
        except Exception:
            logger.exception("Schedule-call admin email failed for quote %s", quote.id)

        # 2. Per-admin in-app bell (URGENT priority) so every dashboard user
        #    sees the badge immediately.
        try:
            from notifications.services.router_service import NotificationRouter
            from accounts.models.user import User

            admins_qs = User.objects.filter(is_active=True).filter(
                is_chief=True
            ) | User.objects.filter(is_active=True, is_superuser=True)
            admins = list(admins_qs.distinct().order_by('-date_joined'))
            if not admins:
                admins = list(User.objects.filter(
                    role=User.Role.PLATFORM_ADMIN, is_active=True
                ).order_by('-date_joined'))

            for admin in admins:
                try:
                    NotificationRouter.route(
                        user=admin,
                        title=title,
                        message=message,
                        notification_type='SYSTEM',
                        priority='URGENT',
                        icon='fa-phone-volume',
                        action_url=dashboard_url,
                        send_email=False,  # already sent to shared inbox above
                        send_sms=False,
                        metadata={
                            'quote_id': quote.id,
                            'preferred_call_time': quote.preferred_call_time,
                            'phone': quote.phone,
                        },
                    )
                except Exception:
                    logger.exception("Schedule-call bell for admin %s failed", admin)
        except Exception as exc:
            logger.warning("Schedule-call bell fan-out failed: %s", exc)

    @classmethod
    def _send_admin_notification(cls, quote: QuoteRequest, request=None) -> None:
        """
        Send admin notification email via Resend.

        Delegates to EmailService.send_admin_quote_alert, which:
          - looks up the admin user from the User model (falls back to ADMIN_EMAIL)
          - renders templates/email/quote_received.html
          - logs the attempt to EmailLog
        """
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

            if sent:
                logger.info(f"Quote notification sent to admin for quote: {quote.id}")
            else:
                logger.warning(
                    f"Quote notification reported failure (no admin user or send failed) "
                    f"for quote: {quote.id}"
                )

        except ImportError:
            # Fallback: Resend direct
            logger.warning("EmailService not found, using fallback email sending")
            cls._send_fallback_email(quote)

        except Exception as e:
            logger.exception(f"Email sending failed for quote {quote.id}: {str(e)}")
            raise

    @classmethod
    def _send_fallback_email(cls, quote: QuoteRequest) -> None:
        """
        Fallback email sending using Resend directly.
        """
        import resend

        resend.api_key = getattr(settings, "RESEND_API_KEY", "")

        if not resend.api_key:
            logger.warning("No RESEND_API_KEY configured, skipping email")
            return

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

        logger.info(f"Fallback quote notification sent to: {admin_email}")

    # ============================================================
    # ADMIN-SIDE METHODS
    # ============================================================

    @classmethod
    def get_admin_quotes(cls, user=None, search=None, project_type=None,
                         budget_range=None, timeline=None, replied=None):
        """
        Get quote requests for admin view with optional filters.

        Returns:
            QuerySet[QuoteRequest]
        """
        qs = QuoteRequest.objects.all().order_by("-created_at")

        if search:
            qs = qs.filter(
                Q(name__icontains=search) |
                Q(email__icontains=search) |
                Q(phone__icontains=search) |
                Q(details__icontains=search)
            )
        if project_type:
            qs = qs.filter(project_type=project_type)
        if budget_range:
            qs = qs.filter(budget_range=budget_range)
        if timeline:
            qs = qs.filter(timeline=timeline)
        if replied is not None:
            qs = qs.filter(is_replied=replied)

        if user:
            AuditService.log_action(
                user=user,
                action="QUOTES_VIEWED",
                entity_type="QuoteRequest",
                details={"filters": {
                    "search": bool(search),
                    "project_type": project_type,
                    "budget_range": budget_range,
                    "timeline": timeline,
                    "replied": replied,
                }},
            )

        return qs

    @classmethod
    def get_quote_by_id(cls, quote_id, user=None):
        """Get a single quote by ID for admin view."""
        try:
            quote = QuoteRequest.objects.get(id=quote_id)
            if user:
                AuditService.log_action(
                    user=user,
                    action="QUOTE_VIEWED",
                    entity_type="QuoteRequest",
                    entity_id=quote.id,
                    details={"name": quote.name, "email": quote.email},
                )
            return quote
        except QuoteRequest.DoesNotExist:
            return None

    @classmethod
    def delete_quote(cls, user, quote):
        """Delete a quote request. Logs audit."""
        snapshot = {
            "id": quote.id,
            "name": quote.name,
            "email": quote.email,
            "project_type": quote.project_type,
            "created_at": quote.created_at.isoformat(),
        }
        quote.delete()
        AuditService.log_action(
            user=user,
            action="QUOTE_DELETED",
            entity_type="QuoteRequest",
            entity_id=snapshot["id"],
            details=snapshot,
        )
        logger.info(f"Quote deleted: {snapshot['id']} by {user.email}")
        return True

    @classmethod
    def mark_replied(cls, user, quote, replied=True):
        """Toggle replied flag on a quote."""
        if replied:
            quote.mark_replied()
        else:
            quote.is_replied = False
            quote.replied_at = None
            quote.save(update_fields=["is_replied", "replied_at"])

        AuditService.log_action(
            user=user,
            action="QUOTE_MARKED_REPLIED" if replied else "QUOTE_MARKED_UNREPLIED",
            entity_type="QuoteRequest",
            entity_id=quote.id,
            details={"name": quote.name, "is_replied": quote.is_replied},
        )
        logger.info(f"Quote {quote.id} marked replied={replied} by {user.email}")
        return quote

    @classmethod
    def get_quote_stats(cls):
        """Aggregate stats for the dashboard quote list."""
        qs = QuoteRequest.objects.all()
        now = timezone.now()
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)

        return {
            "total": qs.count(),
            "unreplied": qs.filter(is_replied=False).count(),
            "replied": qs.filter(is_replied=True).count(),
            "this_week": qs.filter(created_at__gte=week_ago).count(),
            "this_month": qs.filter(created_at__gte=month_ago).count(),
            "by_project_type": {
                pt: qs.filter(project_type=pt).count()
                for pt, _ in QuoteRequest._meta.get_field("project_type").choices
            },
        }