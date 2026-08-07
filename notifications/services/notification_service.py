import logging
from django.utils import timezone
from notifications.models.notification import Notification

logger = logging.getLogger('caldan.notifications')


class NotificationService:
    """Service for creating and managing in-app notifications."""

    @classmethod
    def create(cls, user, title, message, notification_type="SYSTEM", priority="MEDIUM", icon="fa-bell", action_url="#", metadata=None):
        """Create an in-app notification for a user."""
        try:
            notification = Notification.objects.create(
                user=user,
                title=title,
                message=message,
                type=notification_type,
                priority=priority,
                icon=icon,
                action_url=action_url,
                is_read=False,
                metadata=metadata or {}
            )
            logger.info(f"Notification created for {user.email}: {title}")
            return notification
        except Exception as e:
            logger.error(f"Failed to create notification for {user.email}: {str(e)}")
            return None

    @classmethod
    def create_bulk(cls, users, title, message, notification_type="SYSTEM", priority="MEDIUM", icon="fa-bell", action_url="#"):
        """Create notifications for multiple users at once."""
        notifications = []
        for user in users:
            notifications.append(
                Notification(
                    user=user,
                    title=title,
                    message=message,
                    type=notification_type,
                    priority=priority,
                    icon=icon,
                    action_url=action_url,
                    is_read=False,
                )
            )
        created = Notification.objects.bulk_create(notifications)
        logger.info(f"Bulk created {len(created)} notifications")
        return len(created)

    @classmethod
    def mark_as_read(cls, notification_id, user):
        """Mark a notification as read."""
        try:
            notification = Notification.objects.get(id=notification_id, user=user)
            notification.is_read = True
            notification.read_at = timezone.now()
            notification.save(update_fields=['is_read', 'read_at'])
            return True
        except Notification.DoesNotExist:
            logger.warning(f"Notification {notification_id} not found for user {user.email}")
            return False

    @classmethod
    def mark_all_as_read(cls, user):
        """Mark all unread notifications as read for a user."""
        count = Notification.objects.filter(user=user, is_read=False).update(
            is_read=True,
            read_at=timezone.now()
        )
        logger.info(f"Marked {count} notifications as read for {user.email}")
        return count

    @classmethod
    def get_unread_count(cls, user):
        """Get the number of unread notifications for a user."""
        return Notification.objects.filter(user=user, is_read=False).count()

    @classmethod
    def get_recent(cls, user, limit=10):
        """Get recent notifications for a user."""
        return Notification.objects.filter(user=user).order_by('-created_at')[:limit]

    @classmethod
    def get_all(cls, user, page=1, per_page=20):
        """Get paginated notifications for a user."""
        notifications = Notification.objects.filter(user=user).order_by('-created_at')
        total = notifications.count()
        start = (page - 1) * per_page
        end = start + per_page
        return {
            'items': notifications[start:end],
            'total': total,
            'page': page,
            'per_page': per_page,
            'pages': (total + per_page - 1) // per_page if total > 0 else 0,
        }

    @classmethod
    def delete(cls, notification_id, user):
        """Delete a notification."""
        try:
            notification = Notification.objects.get(id=notification_id, user=user)
            notification.delete()
            return True
        except Notification.DoesNotExist:
            return False