"""
Custom User model for Caldan Construction.
Implements OTP-based authentication with SHA-256 hashing.
"""

import hashlib
import secrets
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from cloudinary.models import CloudinaryField


class UserManager(BaseUserManager):
    """
    Custom user manager for Caldan Construction.
    Handles creation of users, superusers, and chief admins.
    """

    def create_user(self, email, password=None, **extra_fields):
        """
        Create and save a regular user with the given email and password.
        """
        if not email:
            raise ValueError(_('Email address is required'))

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """
        Create and save a superuser with the given email and password.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('is_chief', True)
        extra_fields.setdefault('role', User.Role.CHIEF_ADMIN)

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))
        if extra_fields.get('is_chief') is not True:
            raise ValueError(_('Superuser must have is_chief=True.'))

        return self.create_user(email, password, **extra_fields)

    def create_platform_admin(self, email, password=None, **extra_fields):
        """
        Create and save a platform admin (non-chief).
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', False)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('is_chief', False)
        extra_fields.setdefault('role', User.Role.PLATFORM_ADMIN)

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Admin must have is_staff=True.'))
        if extra_fields.get('is_chief') is True:
            raise ValueError(_('Platform Admin cannot be chief.'))

        return self.create_user(email, password, **extra_fields)

    def create_client(self, email, password=None, **extra_fields):
        """
        Create and save a client user.
        """
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('is_chief', False)
        extra_fields.setdefault('role', User.Role.CLIENT)

        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom User model for Caldan Construction.

    Features:
    - Email-based authentication (no username)
    - 8-digit OTP with SHA-256 hashing
    - Role-based access control
    - Trusted devices for "Remember Me"
    - Account lockout on failed attempts
    - Audit logging of all actions
    """

    class Role(models.TextChoices):
        """User roles with hierarchical access."""
        CHIEF_ADMIN = 'CHIEF_ADMIN', _('Chief Admin')
        PLATFORM_ADMIN = 'PLATFORM_ADMIN', _('Platform Admin')
        CLIENT = 'CLIENT', _('Client')

    # =====================================================================
    # IDENTITY FIELDS
    # =====================================================================
    email = models.EmailField(
        _('email address'),
        unique=True,
        db_index=True,
        max_length=254,
        help_text=_('Primary login identifier')
    )
    full_name = models.CharField(_('full name'), max_length=150)
    admin_id = models.CharField(
        _('admin ID'),
        max_length=20,
        blank=True,
        null=True,
        unique=True,
        help_text=_('Format: ADMIN-001, ADMIN-002, etc.')
    )
    phone = models.CharField(_('phone number'), max_length=15)

    # Profile picture — Cloudinary-hosted so it loads fast and resizes
    avatar = CloudinaryField(
        _('profile picture'),
        folder='avatars',
        blank=True,
        null=True,
        help_text=_('Square image, ideally 256×256 or larger. Max 10 MB.'),
    )

    # =====================================================================
    # ROLE & PERMISSIONS
    # =====================================================================
    role = models.CharField(
        _('role'),
        max_length=20,
        choices=Role.choices,
        default=Role.CLIENT,
        db_index=True
    )
    is_active = models.BooleanField(
        _('active'),
        default=True,
        help_text=_('Designates whether this user should be treated as active.')
    )
    is_staff = models.BooleanField(
        _('staff status'),
        default=False,
        help_text=_('Designates whether the user can log into this admin site.')
    )
    is_superuser = models.BooleanField(
        _('superuser status'),
        default=False,
        help_text=_('Designates that this user has all permissions.')
    )
    is_chief = models.BooleanField(
        _('chief admin'),
        default=False,
        help_text=_('Designates the first admin created during setup.')
    )
    is_email_verified = models.BooleanField(
        _('email verified'),
        default=False,
        help_text=_('Designates whether the user has verified their email via OTP.')
    )
    password_change_required = models.BooleanField(
        _('password change required'),
        default=False,
        help_text=_('Force password change on next login.')
    )

    # =====================================================================
    # OTP FIELDS (8-Digit, SHA-256 Hashed)
    # =====================================================================
    otp_code_hash = models.CharField(
        _('OTP hash'),
        max_length=64,
        null=True,
        blank=True,
        help_text=_('SHA-256 hash of the 8-digit OTP code.')
    )
    otp_created_at = models.DateTimeField(
        _('OTP created at'),
        null=True,
        blank=True,
        help_text=_('Timestamp when OTP was generated.')
    )
    otp_attempts = models.PositiveSmallIntegerField(
        _('OTP attempts'),
        default=0,
        help_text=_('Number of failed OTP verification attempts.')
    )
    otp_resend_count = models.PositiveSmallIntegerField(
        _('OTP resend count'),
        default=0,
        help_text=_('Number of OTP resends in current hour.')
    )
    otp_last_resend = models.DateTimeField(
        _('OTP last resend'),
        null=True,
        blank=True,
        help_text=_('Timestamp of the last OTP resend.')
    )

    # =====================================================================
    # TRUSTED DEVICES (Remember Me - 30 Days)
    # =====================================================================
    trusted_devices = models.JSONField(
        _('trusted devices'),
        default=list,
        blank=True,
        help_text=_('List of trusted devices with SHA-256 fingerprints.')
    )

    # =====================================================================
    # SECURITY FIELDS
    # =====================================================================
    failed_login_attempts = models.PositiveSmallIntegerField(
        _('failed login attempts'),
        default=0,
        help_text=_('Number of consecutive failed login attempts.')
    )
    locked_until = models.DateTimeField(
        _('locked until'),
        null=True,
        blank=True,
        help_text=_('Account locked until this timestamp after 5 failed attempts.')
    )

    # =====================================================================
    # TIMESTAMPS
    # =====================================================================
    last_login = models.DateTimeField(_('last login'), null=True, blank=True)
    date_joined = models.DateTimeField(_('date joined'), default=timezone.now)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)

    # =====================================================================
    # META
    # =====================================================================
    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['full_name', 'phone']

    class Meta:
        db_table = 'users'
        verbose_name = _('user')
        verbose_name_plural = _('users')
        ordering = ('-date_joined',)
        indexes = [
            models.Index(fields=['email'], name='users_email_idx'),
            models.Index(fields=['role'], name='users_role_idx'),
            models.Index(fields=['admin_id'], name='users_admin_id_idx'),
            models.Index(fields=['is_active', 'is_chief'], name='users_active_chief_idx'),
            models.Index(fields=['-date_joined'], name='users_date_joined_idx'),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['email'],
                condition=models.Q(is_active=True),
                name='unique_active_email'
            ),
        ]

    def __str__(self):
        """String representation."""
        return f"{self.full_name} ({self.email})"

    # =====================================================================
    # PROPERTIES
    # =====================================================================

    @property
    def is_admin(self):
        """Check if user is any type of admin."""
        return self.role in [self.Role.CHIEF_ADMIN, self.Role.PLATFORM_ADMIN]

    @property
    def is_platform_admin(self):
        """Check if user is a platform admin (not chief)."""
        return self.role == self.Role.PLATFORM_ADMIN

    @property
    def is_client(self):
        """Check if user is a client."""
        return self.role == self.Role.CLIENT

    @property
    def get_admin_id(self):
        """Get admin ID or generate one."""
        if not self.admin_id and self.is_admin:
            return self.generate_admin_id()
        return self.admin_id

    @property
    def role_display(self):
        """Get human-readable role name."""
        return self.get_role_display()

    @property
    def full_name_short(self):
        """Get short name (first name only)."""
        return self.full_name.split()[0] if self.full_name else self.email

    # =====================================================================
    # ADMIN ID GENERATION
    # =====================================================================

    def generate_admin_id(self):
        """
        Generate a unique admin ID in format ADMIN-XXX.
        Only for admin roles.
        """
        if not self.is_admin:
            return None

        # Count existing admins
        count = User.objects.filter(
            role__in=[self.Role.CHIEF_ADMIN, self.Role.PLATFORM_ADMIN]
        ).count()

        # If this is a new user being created, count + 1
        if not self.pk:
            count += 1

        admin_id = f"ADMIN-{count:03d}"

        # Ensure uniqueness
        while User.objects.filter(admin_id=admin_id).exclude(pk=self.pk).exists():
            count += 1
            admin_id = f"ADMIN-{count:03d}"

        self.admin_id = admin_id
        return admin_id

    # =====================================================================
    # OTP METHODS
    # =====================================================================

    def generate_otp(self):
        """
        Generate an 8-digit OTP and store its SHA-256 hash.

        Returns:
            str: The plaintext OTP code (8 digits).
        """
        # Generate 8-digit OTP
        otp_code = ''.join([str(secrets.randbelow(10)) for _ in range(8)])

        # Hash and store
        self.otp_code_hash = hashlib.sha256(otp_code.encode()).hexdigest()
        self.otp_created_at = timezone.now()
        self.otp_attempts = 0
        self.save(update_fields=['otp_code_hash', 'otp_created_at', 'otp_attempts'])

        return otp_code

    def verify_otp(self, otp_code):
        """
        Verify an OTP code against the stored hash.

        Args:
            otp_code (str): The 8-digit OTP code to verify.

        Returns:
            tuple: (success, message)
        """
        from django.conf import settings

        # Check if OTP exists
        if not self.otp_code_hash:
            return False, "No OTP generated"

        # Check expiry (5 minutes)
        expiry_minutes = getattr(settings, 'OTP_EXPIRY_MINUTES', 5)
        if timezone.now() > self.otp_created_at + timezone.timedelta(minutes=expiry_minutes):
            self.clear_otp()
            return False, "OTP expired"

        # Check attempts (max 3)
        max_attempts = getattr(settings, 'OTP_MAX_ATTEMPTS', 3)
        if self.otp_attempts >= max_attempts:
            self.clear_otp()
            return False, "Too many failed attempts. Please request a new OTP."

        # Verify code
        hashed = hashlib.sha256(otp_code.encode()).hexdigest()
        if hashed == self.otp_code_hash:
            # Success - clear OTP and mark email verified
            self.clear_otp()
            self.is_email_verified = True
            self.save(update_fields=['otp_code_hash', 'otp_created_at', 'otp_attempts', 'is_email_verified'])
            return True, "OTP verified successfully"

        # Failed attempt
        self.otp_attempts += 1
        self.save(update_fields=['otp_attempts'])
        remaining = max_attempts - self.otp_attempts
        return False, f"Invalid OTP. {remaining} attempt(s) remaining."

    def clear_otp(self):
        """Clear OTP fields."""
        self.otp_code_hash = None
        self.otp_created_at = None
        self.otp_attempts = 0
        self.save(update_fields=['otp_code_hash', 'otp_created_at', 'otp_attempts'])

    def can_resend_otp(self):
        """
        Check if user can resend OTP.

        Returns:
            tuple: (can_resend, message, wait_seconds)
        """
        from django.conf import settings

        # Check if OTP exists and is still valid
        if self.otp_code_hash and self.otp_created_at:
            expiry_minutes = getattr(settings, 'OTP_EXPIRY_MINUTES', 5)
            if timezone.now() <= self.otp_created_at + timezone.timedelta(minutes=expiry_minutes):
                # OTP is still valid, no need to resend
                remaining = self.otp_created_at + timezone.timedelta(minutes=expiry_minutes) - timezone.now()
                return False, "Current OTP is still valid", int(remaining.total_seconds())

        # Check cooldown (60 seconds)
        cooldown = getattr(settings, 'OTP_RESEND_COOLDOWN_SECONDS', 60)
        if self.otp_last_resend:
            elapsed = (timezone.now() - self.otp_last_resend).total_seconds()
            if elapsed < cooldown:
                wait = int(cooldown - elapsed)
                return False, f"Please wait {wait} seconds before requesting a new OTP", wait

        # Check hourly limit (5 per hour)
        max_resends = getattr(settings, 'OTP_MAX_RESENDS_PER_HOUR', 5)
        if self.otp_resend_count >= max_resends:
            return False, "Maximum OTP resends per hour exceeded. Please try again later.", 0

        return True, "You can request a new OTP", 0

    def mark_otp_resend(self):
        """Record that an OTP was resent."""
        self.otp_resend_count += 1
        self.otp_last_resend = timezone.now()
        self.save(update_fields=['otp_resend_count', 'otp_last_resend'])

    def reset_otp_resend_count(self):
        """Reset OTP resend count (called hourly)."""
        self.otp_resend_count = 0
        self.otp_last_resend = None
        self.save(update_fields=['otp_resend_count', 'otp_last_resend'])

    # =====================================================================
    # TRUSTED DEVICE METHODS
    # =====================================================================

    def generate_device_fingerprint(self, request):
        """
        Generate a unique device fingerprint from request data.

        Args:
            request: Django request object.

        Returns:
            str: SHA-256 fingerprint hash.
        """
        components = [
            request.META.get('HTTP_USER_AGENT', ''),
            request.META.get('HTTP_ACCEPT_LANGUAGE', ''),
            request.META.get('HTTP_ACCEPT_ENCODING', ''),
            request.META.get('REMOTE_ADDR', '').split(',')[0],
            getattr(settings, 'SECRET_KEY', '')[:10],
        ]
        fingerprint = hashlib.sha256(''.join(components).encode()).hexdigest()
        return fingerprint

    def is_trusted_device(self, request):
        """
        Check if the current device is trusted for this user.

        Args:
            request: Django request object.

        Returns:
            bool: True if device is trusted.
        """
        fingerprint = self.generate_device_fingerprint(request)
        devices = self.trusted_devices or []

        for device in devices:
            if device.get('fingerprint') == fingerprint:
                expires_at = device.get('expires_at')
                if expires_at:
                    from datetime import datetime
                    try:
                        expiry = datetime.fromisoformat(expires_at)
                        if timezone.now() < expiry:
                            return True
                    except (ValueError, TypeError):
                        pass
        return False

    def add_trusted_device(self, request):
        """
        Add the current device as trusted for 30 days.

        Args:
            request: Django request object.
        """
        from django.conf import settings

        fingerprint = self.generate_device_fingerprint(request)
        devices = self.trusted_devices or []

        # Limit to 10 devices
        max_devices = getattr(settings, 'MAX_TRUSTED_DEVICES', 10)
        if len(devices) >= max_devices:
            devices = devices[-9:]  # Keep newest 9

        days = getattr(settings, 'TRUSTED_DEVICE_DAYS', 30)

        device_data = {
            'fingerprint': fingerprint,
            'expires_at': (timezone.now() + timezone.timedelta(days=days)).isoformat(),
            'created_at': timezone.now().isoformat(),
            'device_name': request.META.get('HTTP_USER_AGENT', 'Unknown')[:100],
            'ip_address': request.META.get('REMOTE_ADDR', ''),
        }

        devices.append(device_data)
        self.trusted_devices = devices
        self.save(update_fields=['trusted_devices'])

    def remove_trusted_device(self, fingerprint):
        """
        Remove a trusted device by fingerprint.

        Args:
            fingerprint (str): The device fingerprint to remove.
        """
        devices = self.trusted_devices or []
        devices = [d for d in devices if d.get('fingerprint') != fingerprint]
        self.trusted_devices = devices
        self.save(update_fields=['trusted_devices'])

    def clear_trusted_devices(self):
        """Remove all trusted devices."""
        self.trusted_devices = []
        self.save(update_fields=['trusted_devices'])

    # =====================================================================
    # ACCOUNT LOCKOUT METHODS
    # =====================================================================

    def handle_failed_login(self):
        """
        Handle a failed login attempt.
        Locks account after 5 failed attempts for 15 minutes.
        """
        from django.conf import settings

        self.failed_login_attempts += 1

        max_attempts = 5  # Fixed at 5 for security
        if self.failed_login_attempts >= max_attempts:
            self.locked_until = timezone.now() + timezone.timedelta(minutes=15)

        self.save(update_fields=['failed_login_attempts', 'locked_until'])

    def handle_successful_login(self):
        """Reset failed login attempts on successful login."""
        self.failed_login_attempts = 0
        self.locked_until = None
        self.last_login = timezone.now()
        self.save(update_fields=['failed_login_attempts', 'locked_until', 'last_login'])

    def is_account_locked(self):
        """
        Check if account is currently locked.

        Returns:
            tuple: (is_locked, message, remaining_minutes)
        """
        if self.locked_until and self.locked_until > timezone.now():
            remaining = (self.locked_until - timezone.now())
            minutes = int(remaining.total_seconds() / 60)
            return True, f"Account locked for {minutes} minutes due to failed login attempts.", minutes

        # Clear lock if expired
        if self.locked_until and self.locked_until <= timezone.now():
            self.failed_login_attempts = 0
            self.locked_until = None
            self.save(update_fields=['failed_login_attempts', 'locked_until'])

        return False, None, 0

    # =====================================================================
    # PERMISSION HELPERS
    # =====================================================================

    def has_permission(self, permission_name):
        """
        Check if user has a specific permission.

        Args:
            permission_name (str): The permission to check.

        Returns:
            bool: True if user has permission.
        """
        # Chief Admin has all permissions
        if self.is_chief or self.is_superuser:
            return True

        # Check profile permissions
        if hasattr(self, 'profile') and self.profile.permissions:
            return self.profile.permissions.get(permission_name, False)

        # Platform Admin has default full access
        if self.is_platform_admin:
            return True

        return False

    # =====================================================================
    # REQUIRED METHODS FOR DJANGO
    # =====================================================================

    def get_full_name(self):
        """Return the full name of the user."""
        return self.full_name

    def get_short_name(self):
        """Return the short name of the user."""
        return self.full_name_short

    def get_email(self):
        """Return the email of the user."""
        return self.email

    def has_module_perms(self, app_label):
        """
        Return True if user has permissions to view the app `app_label`.
        """
        return self.is_superuser or self.is_chief or self.is_staff

    def has_perm(self, perm, obj=None):
        """
        Return True if user has the specified permission.
        """
        return self.is_superuser or self.is_chief

    # =====================================================================
    # SAVE OVERRIDE
    # =====================================================================

    def save(self, *args, **kwargs):
        """
        Override save to handle admin_id generation and OTP resend count reset.
        """
        # Generate admin_id for admins
        if self.is_admin and not self.admin_id:
            self.generate_admin_id()

        # Reset OTP resend count hourly
        if self.otp_last_resend:
            if timezone.now() > self.otp_last_resend + timezone.timedelta(hours=1):
                self.otp_resend_count = 0

        super().save(*args, **kwargs)