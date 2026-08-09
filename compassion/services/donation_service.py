"""
DonationService — orchestrates the full Donation lifecycle:

  1. create_pending_donation(...) — saves a PENDING row from form data
  2. mark_paid(...) — idempotently flips to SUCCESS, sends emails +
     fires in-app admin notifications, writes audit
  3. get_admin_list(...) — paginated filterable list for the dashboard

Mirrors the architecture of website/services/contact_service.py:
best-effort email/notification fan-out wrapped in try/except so user
flow never breaks. All side effects (audit, email, notification)
happen in services, NOT in views.
"""

import logging
from decimal import Decimal, InvalidOperation

from django.db.models import Q

from accounts.services.audit_service import AuditService

logger = logging.getLogger(__name__)


class DonationService:
    """Service for monetary donations to Caldan Compassionate Ministry."""

    @classmethod
    def create_pending_donation(
        cls,
        *,
        name: str,
        email: str,
        phone: str,
        amount,
        purpose: str,
        note: str = "",
        request=None,
    ):
        """Create a PENDING Donation row from form input.

        Returns the Donation instance. The caller (view) then calls
        PaystackClient.initiate_donation(donation) to obtain an
        authorization_url.
        """
        from compassion.models import Donation

        try:
            amount_decimal = Decimal(str(amount))
        except (InvalidOperation, TypeError, ValueError):
            amount_decimal = Decimal("0.00")

        donation = Donation.objects.create(
            donor_name=(name or "").strip(),
            donor_email=(email or "").strip().lower(),
            donor_phone=(phone or "").strip(),
            amount_ksh=amount_decimal,
            purpose=(purpose or Donation.Purpose.GENERAL),
            note=(note or "").strip(),
            ip_address=AuditService._get_client_ip(request) if request else None,
            user_agent=(request.META.get("HTTP_USER_AGENT", "") if request else "")[:300],
        )

        AuditService.log_action(
            user=None,
            action="DONATION_INITIATED",
            entity_type="Donation",
            entity_id=donation.id,
            details={
                "amount": str(amount_decimal),
                "purpose": donation.purpose,
                "donor_email": donation.donor_email,
            },
            request=request,
        )
        cls._send_admin_initiated_alert(donation)
        logger.info("Donation %s created (pending).", donation.reference)
        return donation

    # ───── State transitions ─────

    @classmethod
    def mark_paid(cls, donation, paystack_reference: str, request=None):
        """Idempotently mark a donation as paid and fan out side effects."""
        if donation.status == donation.Status.SUCCESS:
            return donation  # Already done — webhook + verify may both call us.

        old_status = donation.status
        donation.mark_paid(paystack_reference)

        AuditService.log_action(
            user=None,
            action="DONATION_RECEIVED",
            entity_type="Donation",
            entity_id=donation.id,
            details={
                "amount": str(donation.amount_ksh),
                "reference": paystack_reference,
                "old_status": old_status,
                "donor_email": donation.donor_email,
            },
            request=request,
        )

        cls._send_donor_receipt(donation)
        cls._send_admin_alert(donation)
        cls._notify_admins(donation)

        logger.info("Donation %s marked paid.", donation.reference)
        return donation

    # ───── Email + notification fan-out ─────

    @classmethod
    def _send_donor_receipt(cls, donation) -> None:
        try:
            from notifications.services.email_service import EmailService
            EmailService.send_donation_receipt_with_pdf(donation)
        except Exception as exc:
            logger.exception("Donation donor receipt failed for %s: %s", donation.id, exc)

    @classmethod
    def _send_admin_alert(cls, donation) -> None:
        try:
            from notifications.services.email_service import EmailService
            EmailService.send_donation_admin_alert(donation)
        except Exception as exc:
            logger.exception("Donation admin alert failed for %s: %s", donation.id, exc)

    @classmethod
    def _send_admin_initiated_alert(cls, donation) -> None:
        try:
            from notifications.services.email_service import EmailService
            EmailService.send_donation_initiated_admin(donation)
        except Exception as exc:
            logger.exception("Donation initiated-admin alert failed for %s: %s", donation.id, exc)

    @classmethod
    def _notify_admins(cls, donation) -> None:
        """Light up the in-app bell for every chief admin / superuser."""
        try:
            from accounts.models.user import User
            from notifications.services.router_service import NotificationRouter

            admins = (
                User.objects.filter(is_active=True, is_chief=True)
                | User.objects.filter(is_active=True, is_superuser=True)
            )
            admins = list(admins.distinct())
            if not admins:
                admins = list(
                    User.objects.filter(is_active=True, role=User.Role.PLATFORM_ADMIN)
                )

            title = f"💚 New donation — KES {donation.amount_ksh}"
            message = (
                f"{donation.donor_name} ({donation.donor_email}) gave "
                f"KES {donation.amount_ksh} for {donation.get_purpose_display()}."
            )
            for admin in admins:
                try:
                    NotificationRouter.route(
                        user=admin,
                        title=title,
                        message=message,
                        notification_type="SYSTEM",
                        priority="MEDIUM",
                        icon="fa-hand-holding-heart",
                        action_url=f"/dashboard/compassion/donations/{donation.id}/",
                        send_email=False,  # already sent above
                        send_sms=False,
                        metadata={
                            "donation_id": donation.id,
                            "amount": str(donation.amount_ksh),
                            "reference": donation.reference,
                        },
                    )
                except Exception:
                    logger.exception("NotificationRouter failed for admin %s", admin)
        except Exception as exc:
            logger.warning("Donation admin notification fan-out failed: %s", exc)

    # ───── Admin queries ─────

    @classmethod
    def get_admin_list(cls, *, status=None, purpose=None, search=None, request_user=None):
        """Return queryset for the dashboard donations list with filters."""
        from compassion.models import Donation

        qs = Donation.objects.all().order_by("-created_at")
        if status:
            qs = qs.filter(status=status)
        if purpose:
            qs = qs.filter(purpose=purpose)
        if search:
            qs = qs.filter(
                Q(donor_name__icontains=search)
                | Q(donor_email__icontains=search)
                | Q(reference__icontains=search)
                | Q(paystack_reference__icontains=search)
            )
        if request_user:
            AuditService.log_action(
                user=request_user,
                action="DONATION_LIST_VIEWED",
                entity_type="Donation",
                details={
                    "filters": {
                        "status": bool(status),
                        "purpose": bool(purpose),
                        "search": bool(search),
                    }
                },
            )
        return qs

    @classmethod
    def get_by_id(cls, donation_id, request_user=None):
        from compassion.models import Donation
        try:
            donation = Donation.objects.get(id=donation_id)
            if request_user:
                AuditService.log_action(
                    user=request_user,
                    action="DONATION_VIEWED",
                    entity_type="Donation",
                    entity_id=donation.id,
                    details={"reference": donation.reference},
                )
            return donation
        except Donation.DoesNotExist:
            return None

    @classmethod
    def mark_failed(cls, donation, request=None, reason: str = "") -> None:
        if donation.status == donation.Status.FAILED:
            return
        donation.mark_failed()
        AuditService.log_action(
            user=None,
            action="DONATION_FAILED",
            entity_type="Donation",
            entity_id=donation.id,
            details={"reference": donation.reference, "reason": reason or ""},
            request=request,
        )
        cls._send_admin_failed_alert(donation, reason)

    @classmethod
    def _send_admin_failed_alert(cls, donation, reason: str = "") -> None:
        try:
            from notifications.services.email_service import EmailService
            EmailService.send_donation_failed_admin(donation, reason=reason or "")
        except Exception as exc:
            logger.exception("Donation failed-admin alert failed for %s: %s", donation.id, exc)

    @classmethod
    def mark_abandoned(cls, donation, request=None) -> None:
        if donation.status == donation.Status.ABANDONED:
            return
        donation.status = donation.Status.ABANDONED
        donation.save(update_fields=["status", "updated_at"])
        AuditService.log_action(
            user=None,
            action="DONATION_ABANDONED",
            entity_type="Donation",
            entity_id=donation.id,
            details={"reference": donation.reference},
            request=request,
        )