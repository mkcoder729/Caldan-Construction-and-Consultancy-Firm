import logging
from django.conf import settings
from notifications.services.notification_service import NotificationService
from notifications.services.email_service import EmailService
from notifications.services.sms_service import SMSService

logger = logging.getLogger('caldan.notifications')


class NotificationRouter:
    """
    Routes notifications to appropriate channels based on type and priority.
    """

    @classmethod
    def route(cls, user, title, message, notification_type='SYSTEM', priority='MEDIUM',
              icon='fa-bell', action_url='#', send_email=True, send_sms=False, metadata=None):
        """
        Route a notification to the appropriate channels.

        Args:
            user: The user to notify
            title: Notification title
            message: Notification message
            notification_type: Type of notification (STOCK_ALERT, ORDER_CONFIRMED, etc.)
            priority: LOW, MEDIUM, HIGH, URGENT
            icon: Font Awesome icon class
            action_url: URL to navigate when clicked
            send_email: Whether to send email
            send_sms: Whether to send SMS
            metadata: Additional metadata
        """
        # Always create in-app notification
        notification = NotificationService.create(
            user=user,
            title=title,
            message=message,
            notification_type=notification_type,
            priority=priority,
            icon=icon,
            action_url=action_url,
            metadata=metadata
        )

        # Send email if enabled
        if send_email and user.email:
            EmailService.send_template(
                to_email=user.email,
                subject=title,
                template_name='email/notification.html',
                context={
                    'user': user,
                    'title': title,
                    'message': message,
                    'notification_type': notification_type,
                    'priority': priority,
                    'action_url': action_url,
                },
                user=user,
                email_type=notification_type
            )

        # Send SMS if enabled and user has phone
        if send_sms and user.phone:
            SMSService.send(
                phone_number=user.phone,
                message=f"{title}: {message[:140]}",
                user=user,
                notification_type=notification_type
            )

        return notification

    @classmethod
    def route_bulk(cls, users, title, message, notification_type='SYSTEM', priority='MEDIUM',
                   icon='fa-bell', action_url='#', send_email=True, send_sms=False, metadata=None):
        """
        Route a notification to multiple users.
        """
        results = []
        for user in users:
            result = cls.route(
                user=user,
                title=title,
                message=message,
                notification_type=notification_type,
                priority=priority,
                icon=icon,
                action_url=action_url,
                send_email=send_email,
                send_sms=send_sms,
                metadata=metadata
            )
            results.append(result)
        return results

    @classmethod
    def route_stock_alert(cls, material, admin_user):
        """Route a stock alert notification."""
        title = f"⚠️ LOW STOCK: {material.name}"
        message = f"{material.name} is at {material.current_quantity} {material.get_unit_display()}. Minimum threshold is {material.minimum_threshold} {material.get_unit_display()}."

        return cls.route(
            user=admin_user,
            title=title,
            message=message,
            notification_type='STOCK_ALERT',
            priority='URGENT',
            icon='fa-exclamation-triangle',
            action_url=f'/dashboard/inventory/materials/{material.id}/',
            send_email=True,
            send_sms=True,
            metadata={'material_id': material.id}
        )

    @classmethod
    def route_order_confirmation(cls, order, admin_user):
        """Route an order confirmation notification."""
        title = f"🛒 New Order: {order.order_number}"
        message = f"Order {order.order_number} placed by {order.client_name} for KES {order.total}."

        return cls.route(
            user=admin_user,
            title=title,
            message=message,
            notification_type='ORDER_CONFIRMED',
            priority='MEDIUM',
            icon='fa-shopping-bag',
            action_url=f'/dashboard/shop/orders/{order.id}/',
            send_email=True,
            send_sms=False,
            metadata={'order_id': order.id}
        )

    @classmethod
    def route_payment_received(cls, payment, admin_user):
        """Route a payment received notification."""
        title = f"💰 Payment Received: {payment.get_type_display()}"
        message = f"Payment of KES {payment.amount} received for {payment.project.name}."

        return cls.route(
            user=admin_user,
            title=title,
            message=message,
            notification_type='PAYMENT_RECEIVED',
            priority='LOW',
            icon='fa-money-bill-wave',
            action_url=f'/dashboard/finances/payments/{payment.id}/',
            send_email=True,
            send_sms=False,
            metadata={'payment_id': payment.id}
        )

    @classmethod
    def _iter_admin_users(cls):
        """Yield every admin user that should receive in-app+email alerts.

        Order: chief admins first (highest priority), then superusers,
        then active platform admins. Chief admins are intentionally
        not double-notified if they are also superusers.
        """
        yield from cls._iter_admins(perm_key='can_manage_blog')

    @classmethod
    def _iter_admins(cls, perm_key: str = 'can_manage_blog'):
        """Yield every admin user that should receive admin alerts.

        Single source of truth for "who gets the admin email". Order:
        chief admins (highest priority), then active superusers, then
        any active staff user, then platform_admin users, then Profiles
        whose `permissions[perm_key]` is True.

        ``perm_key`` selects the Profile permission used in the last
        fallback (default ``can_manage_blog``). Use ``can_manage_orders``
        or ``can_manage_payments`` when fanning out transactional admin
        alerts to a different slice of the staff list.
        """
        seen = set()
        try:
            from accounts.models.user import User
        except Exception:
            return
        try:
            for user in User.objects.filter(is_chief=True, is_active=True).order_by('-date_joined'):
                if user.id in seen:
                    continue
                seen.add(user.id)
                yield user
        except Exception:
            pass
        try:
            for user in (
                User.objects.filter(is_superuser=True, is_active=True)
                .exclude(id__in=seen)
                .order_by('-date_joined')
            ):
                seen.add(user.id)
                yield user
        except Exception:
            pass
        try:
            # Any active staff member — broad fallback so transactional
            # alerts aren't lost when the chief/superuser role hasn't
            # been set yet (e.g. freshly seeded dev DB).
            for user in (
                User.objects.filter(is_staff=True, is_active=True)
                .exclude(id__in=seen)
                .order_by('-date_joined')
            ):
                seen.add(user.id)
                yield user
        except Exception:
            pass
        try:
            for user in (
                User.objects.filter(role=getattr(User.Role, 'PLATFORM_ADMIN', 'PLATFORM_ADMIN'), is_active=True)
                .exclude(id__in=seen)
                .order_by('-date_joined')
            ):
                seen.add(user.id)
                yield user
        except Exception:
            pass
        try:
            from accounts.models.profile import Profile
            for profile in (
                Profile.objects.filter(is_active=True)
                .exclude(user_id__in=seen)
                .select_related('user')
            ):
                perms = getattr(profile, 'permissions', None) or {}
                if perms.get(perm_key):
                    if profile.user_id in seen:
                        continue
                    seen.add(profile.user_id)
                    yield profile.user
        except Exception:
            pass

    @classmethod
    def route_blog_post_published(cls, post):
        """Notify every admin that a blog post went live — bell only.

        Creates an in-app Notification for each admin so the dashboard
        bell lights up, but does NOT send an external email — the email
        surface for blog publish events is reserved for the newsletter
        subscriber broadcast (EmailService.send_newsletter_post, fired
        from the blog signal). Sending both would duplicate the alert
        to the dashboard owner's inbox on every save.
        """
        title = f"📝 New blog post: {post.title}"
        message = (
            f"{post.title} was just published on the Caldan Construction "
            f"and Consultancy Firm blog."
        )
        action_url = f"/blog/{post.slug}/"
        results = []
        for admin in cls._iter_admin_users():
            try:
                results.append(cls.route(
                    user=admin,
                    title=title,
                    message=message,
                    notification_type='PROJECT_UPDATE',
                    priority='LOW',
                    icon='fa-newspaper',
                    action_url=action_url,
                    send_email=False,  # bell only — newsletter broadcast handles email
                    send_sms=False,
                    metadata={
                        'post_id': post.id,
                        'slug': post.slug,
                        'published_at': post.published_at.isoformat() if post.published_at else None,
                    },
                ))
            except Exception:
                logger.exception("route_blog_post_published: failed for user %s", admin)
        return results