"""
Notification signal handlers.

These receivers fire whenever key business events occur (an order is
placed, a payment is received) and route a notification through
`NotificationRouter` so the in-app bell, email, and (optionally) SMS
channels all get the alert.
"""

import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger('caldan.notifications')


def _pick_admin():
    """
    Pick the highest-priority admin to notify (chief → superuser →
    platform admin). Falls back through every active admin role so
    that in dev environments where the chief user is inactive, the
    order/payment emails still go somewhere.

    Delegates to NotificationRouter._iter_admins so the recipient
    ordering stays consistent with every other admin fan-out (blog
    publish, blog post, schedule-call, etc.).
    """
    try:
        from notifications.services.router_service import NotificationRouter
        return next(iter(NotificationRouter._iter_admins(perm_key='can_manage_orders')), None)
    except Exception:
        logger.exception("_pick_admin failed; admin email will be skipped.")
        return None


@receiver(post_save, sender='shop.Order')
def order_post_save(sender, instance, created, **kwargs):
    """
    Notify admins when a new order is placed.

    Fans out to every eligible admin (chief → superuser → staff →
    platform admin). The `route_order_confirmation` helper on
    `NotificationRouter` handles the in-app / email / SMS fan-out
    for a single user; we loop so multiple admins each get a bell +
    email alert.
    """
    if not created:
        return
    try:
        from notifications.services.router_service import NotificationRouter
        admins = list(NotificationRouter._iter_admins(perm_key='can_manage_orders'))
        if not admins:
            logger.warning(
                "order_post_save: no admin available (no active chief/superuser/platform_admin). "
                "Admin email for order %s NOT sent.",
                getattr(instance, "order_number", instance.pk),
            )
            return
        for admin in admins:
            try:
                NotificationRouter.route_order_confirmation(instance, admin)
            except Exception:
                logger.exception("order_post_save: route_order_confirmation failed for admin %s", admin)
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("order_post_save failed: %s", exc)


@receiver(post_save, sender='finances.Payment')
def payment_post_save(sender, instance, created, **kwargs):
    """
    Notify admins when a payment is recorded.

    We only fire on create to avoid duplicate notifications when
    status flips (e.g. PENDING → COMPLETED) on an existing row.
    """
    if not created:
        return
    try:
        from notifications.services.router_service import NotificationRouter
        admins = list(NotificationRouter._iter_admins(perm_key='can_manage_payments'))
        if not admins:
            logger.warning(
                "payment_post_save: no admin available (no active chief/superuser/platform_admin). "
                "Admin email for payment %s NOT sent.",
                getattr(instance, "id", None),
            )
            return
        for admin in admins:
            try:
                NotificationRouter.route_payment_received(instance, admin)
            except Exception:
                logger.exception("payment_post_save: route_payment_received failed for admin %s", admin)

        # Also email a payment receipt to the customer (payer).
        try:
            from notifications.services.email_service import EmailService
            EmailService.send_payment_receipt(instance)
        except Exception:
            logger.exception("payment_post_save: send_payment_receipt failed")
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("payment_post_save failed: %s", exc)
