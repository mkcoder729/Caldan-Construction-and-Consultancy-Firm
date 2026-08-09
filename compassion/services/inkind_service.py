"""
InKindService — handles in-kind pledges (food / clothing / medical /
other). Mirrors DonationService's pattern: create + workflow advance +
email + admin notification fan-out, all best-effort.
"""

import logging

from accounts.services.audit_service import AuditService

logger = logging.getLogger(__name__)


class InKindService:
    @classmethod
    def create_pledge(
        cls,
        *,
        name: str,
        email: str,
        phone: str,
        item_type: str,
        item_description: str,
        quantity_estimate: str = "",
        delivery_mode: str = "",
        preferred_date=None,
        address: str = "",
        notes: str = "",
        request=None,
    ):
        """Create an in-kind pledge in PLEDGED status."""
        from compassion.models import InKindDonation

        pledge = InKindDonation.objects.create(
            donor_name=(name or "").strip(),
            donor_email=(email or "").strip().lower(),
            donor_phone=(phone or "").strip(),
            item_type=item_type or InKindDonation.ItemType.OTHER,
            item_description=(item_description or "").strip(),
            quantity_estimate=(quantity_estimate or "").strip(),
            delivery_mode=delivery_mode or InKindDonation.DeliveryMode.ARRANGE,
            preferred_date=preferred_date or None,
            address=(address or "").strip(),
            notes=(notes or "").strip(),
            ip_address=AuditService._get_client_ip(request) if request else None,
            user_agent=(request.META.get("HTTP_USER_AGENT", "") if request else "")[:300],
        )

        AuditService.log_action(
            user=None,
            action="INKIND_PLEDGED",
            entity_type="InKindDonation",
            entity_id=pledge.id,
            details={
                "item_type": pledge.item_type,
                "donor_email": pledge.donor_email,
            },
            request=request,
        )

        cls._send_donor_confirmation(pledge)
        cls._send_admin_alert(pledge)
        cls._notify_admins(pledge)
        return pledge

    @classmethod
    def advance_status(cls, pledge, new_status: str, user=None, request=None) -> None:
        from compassion.models import InKindDonation

        if new_status not in InKindDonation.Status.values:
            raise ValueError(f"Invalid status: {new_status}")
        old_status = pledge.status
        if old_status == new_status:
            return

        pledge.advance_to(new_status)
        AuditService.log_action(
            user=user,
            action="INKIND_STATUS_CHANGED",
            entity_type="InKindDonation",
            entity_id=pledge.id,
            details={"old": old_status, "new": new_status},
            request=request,
        )
        cls._send_donor_status_update(pledge, old_status, new_status)
        logger.info("InKind pledge %s: %s → %s", pledge.id, old_status, new_status)

    # ───── Side effects ─────

    @classmethod
    def _send_donor_confirmation(cls, pledge) -> None:
        try:
            from notifications.services.email_service import EmailService
            EmailService.send_inkind_pledge_donor_with_pdf(pledge)
        except Exception as exc:
            logger.exception("InKind donor confirmation failed for %s: %s", pledge.id, exc)

    @classmethod
    def _send_admin_alert(cls, pledge) -> None:
        try:
            from notifications.services.email_service import EmailService
            EmailService.send_inkind_pledge_admin(pledge)
        except Exception as exc:
            logger.exception("InKind admin alert failed for %s: %s", pledge.id, exc)

    @classmethod
    def _send_donor_status_update(cls, pledge, old_status: str, new_status: str) -> None:
        try:
            from notifications.services.email_service import EmailService
            EmailService.send_inkind_status_change_donor(
                pledge, old_status=old_status, new_status=new_status
            )
        except Exception as exc:
            logger.exception(
                "InKind donor status update failed for %s: %s", pledge.id, exc
            )

    @classmethod
    def _notify_admins(cls, pledge) -> None:
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

            title = f"📦 New in-kind pledge — {pledge.get_item_type_display()}"
            message = (
                f"{pledge.donor_name} pledged {pledge.quantity_estimate or 'some'} "
                f"{pledge.get_item_type_display()}."
            )
            for admin in admins:
                try:
                    NotificationRouter.route(
                        user=admin,
                        title=title,
                        message=message,
                        notification_type="SYSTEM",
                        priority="MEDIUM",
                        icon="fa-box-open",
                        action_url=f"/dashboard/compassion/inkind/{pledge.id}/",
                        send_email=False,
                        send_sms=False,
                        metadata={
                            "pledge_id": pledge.id,
                            "item_type": pledge.item_type,
                        },
                    )
                except Exception:
                    logger.exception("NotificationRouter failed for admin %s", admin)
        except Exception as exc:
            logger.warning("InKind admin notification fan-out failed: %s", exc)

    # ───── Admin queries ─────

    @classmethod
    def get_admin_list(cls, *, status=None, item_type=None, search=None, request_user=None):
        from compassion.models import InKindDonation
        from django.db.models import Q

        qs = InKindDonation.objects.all().order_by("-created_at")
        if status:
            qs = qs.filter(status=status)
        if item_type:
            qs = qs.filter(item_type=item_type)
        if search:
            qs = qs.filter(
                Q(donor_name__icontains=search)
                | Q(donor_email__icontains=search)
                | Q(item_description__icontains=search)
            )
        if request_user:
            AuditService.log_action(
                user=request_user,
                action="INKIND_LIST_VIEWED",
                entity_type="InKindDonation",
                details={"filters": {"status": bool(status), "item_type": bool(item_type), "search": bool(search)}},
            )
        return qs