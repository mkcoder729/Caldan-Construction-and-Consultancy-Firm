"""
ScheduleService — handles "schedule a call" requests. Same fan-out
pattern as the donation / in-kind services.
"""

import logging

from accounts.services.audit_service import AuditService

logger = logging.getLogger(__name__)


class ScheduleService:
    @classmethod
    def create_call_request(
        cls,
        *,
        name: str,
        email: str,
        phone: str,
        topic: str,
        preferred_time: str,
        message: str = "",
        request=None,
    ):
        from compassion.models import ScheduleCall

        call = ScheduleCall.objects.create(
            name=(name or "").strip(),
            email=(email or "").strip().lower(),
            phone=(phone or "").strip(),
            topic=topic or ScheduleCall.Topic.GENERAL,
            preferred_time=(preferred_time or "").strip(),
            message=(message or "").strip(),
            ip_address=AuditService._get_client_ip(request) if request else None,
            user_agent=(request.META.get("HTTP_USER_AGENT", "") if request else "")[:300],
        )

        AuditService.log_action(
            user=None,
            action="CALL_REQUESTED",
            entity_type="ScheduleCall",
            entity_id=call.id,
            details={"topic": call.topic, "email": call.email},
            request=request,
        )

        cls._send_donor_confirmation(call)
        cls._send_admin_alert(call)
        cls._notify_admins(call)
        return call

    @classmethod
    def advance_status(cls, call, new_status: str, user=None, request=None) -> None:
        from compassion.models import ScheduleCall

        if new_status not in ScheduleCall.Status.values:
            raise ValueError(f"Invalid status: {new_status}")
        old_status = call.status
        if old_status == new_status:
            return

        call.advance_to(new_status)
        AuditService.log_action(
            user=user,
            action="CALL_STATUS_CHANGED",
            entity_type="ScheduleCall",
            entity_id=call.id,
            details={"old": old_status, "new": new_status},
            request=request,
        )
        cls._send_donor_status_update(call, old_status, new_status)

    # ───── Side effects ─────

    @classmethod
    def _send_donor_confirmation(cls, call) -> None:
        try:
            from notifications.services.email_service import EmailService
            EmailService.send_schedule_call_donor_with_pdf(call)
        except Exception as exc:
            logger.exception("Schedule donor confirmation failed for %s: %s", call.id, exc)

    @classmethod
    def _send_admin_alert(cls, call) -> None:
        try:
            from notifications.services.email_service import EmailService
            EmailService.send_schedule_call_admin(call)
        except Exception as exc:
            logger.exception("Schedule admin alert failed for %s: %s", call.id, exc)

    @classmethod
    def _send_donor_status_update(cls, call, old_status: str, new_status: str) -> None:
        try:
            from notifications.services.email_service import EmailService
            EmailService.send_schedule_call_status_change_donor(
                call, old_status=old_status, new_status=new_status
            )
        except Exception as exc:
            logger.exception(
                "Schedule donor status update failed for %s: %s", call.id, exc
            )

    @classmethod
    def _notify_admins(cls, call) -> None:
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

            title = f"📞 Call requested — {call.get_topic_display()}"
            message = (
                f"{call.name} ({call.phone}) wants to be called — "
                f"preferred window: {call.preferred_time}."
            )
            for admin in admins:
                try:
                    NotificationRouter.route(
                        user=admin,
                        title=title,
                        message=message,
                        notification_type="SYSTEM",
                        priority="MEDIUM",
                        icon="fa-phone",
                        action_url=f"/dashboard/compassion/calls/{call.id}/",
                        send_email=False,
                        send_sms=False,
                        metadata={"call_id": call.id, "topic": call.topic},
                    )
                except Exception:
                    logger.exception("NotificationRouter failed for admin %s", admin)
        except Exception as exc:
            logger.warning("Schedule admin notification fan-out failed: %s", exc)

    # ───── Admin queries ─────

    @classmethod
    def get_admin_list(cls, *, status=None, topic=None, search=None, request_user=None):
        from compassion.models import ScheduleCall
        from django.db.models import Q

        qs = ScheduleCall.objects.all().order_by("-created_at")
        if status:
            qs = qs.filter(status=status)
        if topic:
            qs = qs.filter(topic=topic)
        if search:
            qs = qs.filter(
                Q(name__icontains=search) | Q(email__icontains=search) | Q(message__icontains=search)
            )
        if request_user:
            AuditService.log_action(
                user=request_user,
                action="CALL_LIST_VIEWED",
                entity_type="ScheduleCall",
                details={"filters": {"status": bool(status), "topic": bool(topic), "search": bool(search)}},
            )
        return qs