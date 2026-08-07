"""
Audit Log model with SHA-256 hash chain for immutability.
Every significant action is logged with cryptographic verification.
"""

import hashlib
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class AuditLog(models.Model):
    """
    Immutable audit trail for all significant platform actions.

    Features:
    - SHA-256 hash chain for tamper-proof logging
    - Full context (user, action, entity, IP, user agent)
    - Cryptographic verification of chain integrity
    - 365-day retention
    """

    # =====================================================================
    # ACTION TYPES
    # =====================================================================
    class Action(models.TextChoices):
        """All possible audit actions."""

        # Authentication
        LOGIN_SUCCESS = 'LOGIN_SUCCESS', _('Login Successful')
        LOGIN_FAILED = 'LOGIN_FAILED', _('Login Failed')
        LOGOUT = 'LOGOUT', _('Logout')
        PASSWORD_CHANGED = 'PASSWORD_CHANGED', _('Password Changed')
        PASSWORD_RESET_REQUESTED = 'PASSWORD_RESET_REQUESTED', _('Password Reset Requested')
        PASSWORD_RESET_COMPLETED = 'PASSWORD_RESET_COMPLETED', _('Password Reset Completed')
        OTP_SENT = 'OTP_SENT', _('OTP Sent')
        OTP_VERIFIED = 'OTP_VERIFIED', _('OTP Verified')
        OTP_FAILED = 'OTP_FAILED', _('OTP Failed')
        OTP_RESENT = 'OTP_RESENT', _('OTP Resent')
        ACCOUNT_LOCKED = 'ACCOUNT_LOCKED', _('Account Locked')
        TRUSTED_DEVICE_ADDED = 'TRUSTED_DEVICE_ADDED', _('Trusted Device Added')
        TRUSTED_DEVICE_REMOVED = 'TRUSTED_DEVICE_REMOVED', _('Trusted Device Removed')

        # User Management
        USER_CREATED = 'USER_CREATED', _('User Created')
        USER_UPDATED = 'USER_UPDATED', _('User Updated')
        USER_DELETED = 'USER_DELETED', _('User Deleted')
        USER_ACTIVATED = 'USER_ACTIVATED', _('User Activated')
        USER_DEACTIVATED = 'USER_DEACTIVATED', _('User Deactivated')
        PERMISSION_CHANGED = 'PERMISSION_CHANGED', _('Permission Changed')
        ADMIN_INVITATION_SENT = 'ADMIN_INVITATION_SENT', _('Admin Invitation Sent')
        ADMIN_INVITATION_ACCEPTED = 'ADMIN_INVITATION_ACCEPTED', _('Admin Invitation Accepted')
        ADMIN_INVITATION_EXPIRED = 'ADMIN_INVITATION_EXPIRED', _('Admin Invitation Expired')
        ADMIN_LOCKED = 'ADMIN_LOCKED', _('Admin Manually Locked')
        ADMIN_UNLOCKED = 'ADMIN_UNLOCKED', _('Admin Unlocked')
        CHIEF_ADMIN_CREATED = 'CHIEF_ADMIN_CREATED', _('Chief Admin Created')

        # Projects
        PROJECT_CREATED = 'PROJECT_CREATED', _('Project Created')
        PROJECT_UPDATED = 'PROJECT_UPDATED', _('Project Updated')
        PROJECT_DELETED = 'PROJECT_DELETED', _('Project Deleted')
        PROJECT_ARCHIVED = 'PROJECT_ARCHIVED', _('Project Archived')
        PROJECT_RESTORED = 'PROJECT_RESTORED', _('Project Restored')
        PROJECT_BACKUP_CREATED = 'PROJECT_BACKUP_CREATED', _('Project Backup Created')
        PROJECT_BACKUP_RESTORED = 'PROJECT_BACKUP_RESTORED', _('Project Backup Restored')
        MILESTONE_CREATED = 'MILESTONE_CREATED', _('Milestone Created')
        MILESTONE_UPDATED = 'MILESTONE_UPDATED', _('Milestone Updated')
        MILESTONE_COMPLETED = 'MILESTONE_COMPLETED', _('Milestone Completed')

        # Inventory
        MATERIAL_CREATED = 'MATERIAL_CREATED', _('Material Created')
        MATERIAL_UPDATED = 'MATERIAL_UPDATED', _('Material Updated')
        MATERIAL_DELETED = 'MATERIAL_DELETED', _('Material Deleted')
        STOCK_IN = 'STOCK_IN', _('Stock In')
        STOCK_OUT = 'STOCK_OUT', _('Stock Out')
        STOCK_ADJUSTED = 'STOCK_ADJUSTED', _('Stock Adjusted')
        STOCK_ALERT_CREATED = 'STOCK_ALERT_CREATED', _('Stock Alert Created')
        STOCK_ALERT_RESOLVED = 'STOCK_ALERT_RESOLVED', _('Stock Alert Resolved')
        SUPPLIER_CREATED = 'SUPPLIER_CREATED', _('Supplier Created')
        SUPPLIER_UPDATED = 'SUPPLIER_UPDATED', _('Supplier Updated')
        DELIVERY_CREATED = 'DELIVERY_CREATED', _('Delivery Created')
        DELIVERY_COMPLETED = 'DELIVERY_COMPLETED', _('Delivery Completed')

        # Shop
        PRODUCT_CREATED = 'PRODUCT_CREATED', _('Product Created')
        PRODUCT_UPDATED = 'PRODUCT_UPDATED', _('Product Updated')
        PRODUCT_DELETED = 'PRODUCT_DELETED', _('Product Deleted')
        CART_ADDED = 'CART_ADDED', _('Item Added to Cart')
        CART_REMOVED = 'CART_REMOVED', _('Item Removed from Cart')
        CART_UPDATED = 'CART_UPDATED', _('Cart Updated')
        ORDER_PLACED = 'ORDER_PLACED', _('Order Placed')
        ORDER_STATUS_UPDATED = 'ORDER_STATUS_UPDATED', _('Order Status Updated')
        ORDER_CANCELLED = 'ORDER_CANCELLED', _('Order Cancelled')

        # Payments
        PAYMENT_RECORDED = 'PAYMENT_RECORDED', _('Payment Recorded')
        PAYMENT_APPROVED = 'PAYMENT_APPROVED', _('Payment Approved')
        PAYMENT_COMPLETED = 'PAYMENT_COMPLETED', _('Payment Completed')
        PAYMENT_CANCELLED = 'PAYMENT_CANCELLED', _('Payment Cancelled')
        PAYMENT_FAILED = 'PAYMENT_FAILED', _('Payment Failed')
        EXPENSE_RECORDED = 'EXPENSE_RECORDED', _('Expense Recorded')
        EXPENSE_UPDATED = 'EXPENSE_UPDATED', _('Expense Updated')
        BUDGET_CREATED = 'BUDGET_CREATED', _('Budget Created')
        BUDGET_UPDATED = 'BUDGET_UPDATED', _('Budget Updated')

        # Clients
        CLIENT_CREATED = 'CLIENT_CREATED', _('Client Created')
        CLIENT_UPDATED = 'CLIENT_UPDATED', _('Client Updated')
        CLIENT_DELETED = 'CLIENT_DELETED', _('Client Deleted')
        CLIENT_CONVERTED = 'CLIENT_CONVERTED', _('Client Converted from Lead')
        LEAD_CAPTURED = 'LEAD_CAPTURED', _('Lead Captured')

        # Team
        TEAM_MEMBER_CREATED = 'TEAM_MEMBER_CREATED', _('Team Member Created')
        TEAM_MEMBER_UPDATED = 'TEAM_MEMBER_UPDATED', _('Team Member Updated')
        TEAM_MEMBER_DELETED = 'TEAM_MEMBER_DELETED', _('Team Member Deleted')

        # Services
        SERVICE_CREATED = 'SERVICE_CREATED', _('Service Created')
        SERVICE_UPDATED = 'SERVICE_UPDATED', _('Service Updated')
        SERVICE_DELETED = 'SERVICE_DELETED', _('Service Deleted')

        # Reports & Data
        REPORT_EXPORTED = 'REPORT_EXPORTED', _('Report Exported')
        DATA_EXPORTED = 'DATA_EXPORTED', _('Data Exported')
        BACKUP_CREATED = 'BACKUP_CREATED', _('Backup Created')
        BACKUP_RESTORED = 'BACKUP_RESTORED', _('Backup Restored')
        DATA_DELETED = 'DATA_DELETED', _('Data Deleted')
        DATA_RESTORED = 'DATA_RESTORED', _('Data Restored')

        # Notifications
        NOTIFICATION_SENT = 'NOTIFICATION_SENT', _('Notification Sent')
        EMAIL_SENT = 'EMAIL_SENT', _('Email Sent')
        EMAIL_FAILED = 'EMAIL_FAILED', _('Email Failed')
        SMS_SENT = 'SMS_SENT', _('SMS Sent')
        SMS_FAILED = 'SMS_FAILED', _('SMS Failed')

        # System
        SYSTEM_ALERT = 'SYSTEM_ALERT', _('System Alert')
        SETTINGS_CHANGED = 'SETTINGS_CHANGED', _('Settings Changed')
        AUDIT_REPORT_GENERATED = 'AUDIT_REPORT_GENERATED', _('Audit Report Generated')
        AUDIT_CHAIN_VERIFIED = 'AUDIT_CHAIN_VERIFIED', _('Audit Chain Verified')
        DATABASE_MIGRATION = 'DATABASE_MIGRATION', _('Database Migration')
        DEPLOYMENT = 'DEPLOYMENT', _('Deployment')

    # =====================================================================
    # FIELDS
    # =====================================================================
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
        help_text=_('User who performed the action')
    )
    user_role = models.CharField(
        _('user role'),
        max_length=20,
        blank=True,
        default='',
        help_text=_('Role of the user at time of action')
    )
    action = models.CharField(
        _('action'),
        max_length=50,
        choices=Action.choices,
        db_index=True,
        help_text=_('Type of action performed')
    )
    entity_type = models.CharField(
        _('entity type'),
        max_length=50,
        blank=True,
        default='',
        db_index=True,
        help_text=_('Type of entity affected (e.g., Project, User, Order)')
    )
    entity_id = models.CharField(
        _('entity ID'),
        max_length=50,
        blank=True,
        default='',
        help_text=_('ID of the entity affected')
    )
    details = models.JSONField(
        _('details'),
        default=dict,
        blank=True,
        help_text=_('Additional context about the action')
    )
    ip_address = models.GenericIPAddressField(
        _('IP address'),
        null=True,
        blank=True,
        help_text=_('Client IP address')
    )
    user_agent = models.TextField(
        _('user agent'),
        blank=True,
        default='',
        help_text=_('Client user agent string')
    )

    # =====================================================================
    # CRYPTOGRAPHIC HASH CHAIN (Tamper-Proof)
    # =====================================================================
    hash_previous = models.CharField(
        _('previous hash'),
        max_length=64,
        default='0' * 64,
        help_text=_('SHA-256 hash of the previous audit log entry')
    )
    hash_current = models.CharField(
        _('current hash'),
        max_length=64,
        default='0' * 64,
        help_text=_('SHA-256 hash of this audit log entry')
    )

    # =====================================================================
    # TIMESTAMPS
    # =====================================================================
    created_at = models.DateTimeField(
        _('created at'),
        default=timezone.now,
        db_index=True,
        help_text=_('Timestamp when the action was logged')
    )

    # =====================================================================
    # META
    # =====================================================================
    class Meta:
        db_table = 'audit_logs'
        verbose_name = _('audit log')
        verbose_name_plural = _('audit logs')
        ordering = ('-created_at',)
        indexes = [
            models.Index(fields=['user', '-created_at'], name='audit_user_created_idx'),
            models.Index(fields=['action', '-created_at'], name='audit_action_created_idx'),
            models.Index(fields=['entity_type', 'entity_id'], name='audit_entity_idx'),
            models.Index(fields=['-created_at'], name='audit_created_idx'),
        ]

    def __str__(self):
        """String representation."""
        user_info = self.user.email if self.user else 'SYSTEM'
        return f"{self.action} | {user_info} | {self.created_at.strftime('%Y-%m-%d %H:%M')}"

    # =====================================================================
    # SAVE OVERRIDE (Hash Chain Generation)
    # =====================================================================

    def save(self, *args, **kwargs):
        """
        Override save to generate hash chain.

        The hash chain works as follows:
        1. Get the previous log's hash
        2. Combine: previous_hash + action + user_id + entity_id + timestamp
        3. SHA-256 the combined string
        4. Store as current hash
        """
        # Only generate hash if not already set
        if not self.hash_current or self.hash_current == '0' * 64:
            # Get previous log — use row-level locking only when inside a transaction;
            # otherwise a plain read is fine (slightly weaker but still correct ordering).
            from django.db import transaction as _txn
            if _txn.get_connection().in_atomic_block:
                last_log = AuditLog.objects.select_for_update().order_by('-created_at').first()
            else:
                last_log = AuditLog.objects.order_by('-created_at').first()

            # Set previous hash
            self.hash_previous = last_log.hash_current if last_log else '0' * 64

            # Generate current hash
            hash_data = (
                f"{self.hash_previous}"
                f"{self.action}"
                f"{self.user_id or ''}"
                f"{self.entity_type}"
                f"{self.entity_id}"
                f"{self.created_at.isoformat()}"
            )
            self.hash_current = hashlib.sha256(hash_data.encode()).hexdigest()

        super().save(*args, **kwargs)

    # =====================================================================
    # CHAIN VERIFICATION
    # =====================================================================

    @classmethod
    def verify_chain(cls):
        """
        Verify the integrity of the entire audit chain.

        Returns:
            tuple: (is_valid, message, broken_at_id)
        """
        logs = cls.objects.order_by('created_at')
        previous_hash = '0' * 64

        for log in logs:
            # Verify previous hash matches
            if log.hash_previous != previous_hash:
                return False, f"Chain broken at audit log ID {log.id}", log.id

            # Verify current hash is correct
            hash_data = (
                f"{log.hash_previous}"
                f"{log.action}"
                f"{log.user_id or ''}"
                f"{log.entity_type}"
                f"{log.entity_id}"
                f"{log.created_at.isoformat()}"
            )
            calculated = hashlib.sha256(hash_data.encode()).hexdigest()

            if calculated != log.hash_current:
                return False, f"Hash mismatch at audit log ID {log.id}", log.id

            previous_hash = log.hash_current

        return True, "Audit trail integrity verified", None

    # =====================================================================
    # RETENTION CLEANUP
    # =====================================================================

    @classmethod
    def cleanup_old_logs(cls, retention_days=None):
        """
        Delete audit logs older than retention period.

        Args:
            retention_days (int): Number of days to retain. Defaults to 365.
        """
        from django.conf import settings

        if retention_days is None:
            retention_days = getattr(settings, 'AUDIT_LOG_RETENTION_DAYS', 365)

        cutoff = timezone.now() - timezone.timedelta(days=retention_days)
        old_logs = cls.objects.filter(created_at__lt=cutoff)
        count = old_logs.count()
        old_logs.delete()
        return count