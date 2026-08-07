"""
Invitation Service - Secure admin invitation management.

This service handles the creation, validation, and acceptance of admin
invitations with 48-hour expiry and one-time use tokens.
"""

import logging
import secrets
import string
from typing import Tuple, Optional, Dict, Any
from django.core.mail import send_mail
from django.utils import timezone
from django.conf import settings
from django.urls import reverse
from django.db import transaction
from django.template.loader import render_to_string

from accounts.models import AdminInvitation, User
from accounts.services.audit_service import AuditService
from accounts.services.otp_service import OTPService

logger = logging.getLogger('caldan')


class InvitationService:
    """
    Service for admin invitation management.

    Features:
    - Secure token generation (64-character URL-safe)
    - 48-hour expiry
    - One-time use
    - Email + SMS delivery (each channel independently tracked)
    - Up-front collection of full_name / phone / role / permissions /
      personal message so the acceptance step is short.
    - Audit logging for all actions
    """

    INVITATION_EXPIRY_HOURS = 48

    # =====================================================================
    # CREATE INVITATION
    # =====================================================================
    @classmethod
    def create_invitation(
            cls,
            email: str,
            created_by: User,
            request=None,
            *,
            full_name: str = '',
            phone: str = '',
            role: str = User.Role.PLATFORM_ADMIN,
            permissions: Optional[Dict[str, bool]] = None,
            personal_message: str = '',
            send_email: bool = True,
            send_sms: bool = False,
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Create a secure admin invitation and send via the requested channels.

        Args:
            email: Email address to invite
            created_by: User creating the invitation (must be admin)
            request: Django request object
            full_name: Optional full name (pre-fills acceptance page)
            phone: Optional Kenyan phone number; required for SMS channel
            role: Requested admin role (defaults to PLATFORM_ADMIN)
            permissions: Initial permission toggles to set on acceptance
            personal_message: Optional personal note shown in the email
            send_email: Send via EmailService
            send_sms: Send via SMSService (only if `phone` is set)

        Returns:
            Tuple: (success, response_data)
                On success: response_data includes ``channels`` mapping
                ({"email": {"ok": bool, "error": str|None},
                  "sms":   {"ok": bool, "error": str|None}}).
                The overall success flag is True iff at least one
                channel succeeded — the chief may want to retry the
                broken channel via the Resend row action.
        """
        # Validate that created_by is an admin
        if not created_by.is_admin:
            return False, {
                'error': 'Only admins can create invitations',
                'code': 'PERMISSION_DENIED'
            }

        # Must send something
        if not send_email and not send_sms:
            return False, {
                'error': 'Select at least one delivery channel (Email or SMS).',
                'code': 'NO_CHANNEL_SELECTED',
            }

        # SMS requires a phone
        if send_sms and not phone:
            return False, {
                'error': 'A phone number is required to send via SMS.',
                'code': 'PHONE_REQUIRED_FOR_SMS',
            }

        # Check if user already exists
        if User.objects.filter(email=email).exists():
            return False, {
                'error': 'A user with this email already exists',
                'code': 'USER_EXISTS'
            }

        # Check if there's already a valid invitation
        existing_invitation = AdminInvitation.objects.filter(
            email=email,
            is_accepted=False,
            expires_at__gt=timezone.now()
        ).first()

        if existing_invitation:
            return False, {
                'error': 'An invitation has already been sent to this email',
                'code': 'INVITATION_EXISTS'
            }

        # Auto-generate a temporary password. Mixed-case letters + digits,
        # 12 chars, ambiguous chars removed for readability. Strength
        # check: must include both case classes and at least one digit.
        temp_password = cls._generate_temporary_password()

        # Create invitation
        invitation = AdminInvitation.objects.create(
            email=email,
            created_by=created_by,
            full_name=full_name or '',
            phone=phone or '',
            role=role or User.Role.PLATFORM_ADMIN,
            permissions_json=permissions or {},
            personal_message=personal_message or '',
            temp_password=temp_password,
        )

        # Send via each requested channel. Each channel is independent so a
        # failure on one does not delete the invitation — the chief can use
        # the Resend row action to retry the broken channel.
        channels: Dict[str, Dict[str, Any]] = {
            'email': {'ok': False, 'error': None},
            'sms':   {'ok': False, 'error': None},
        }

        if send_email:
            ok, err = cls._send_invitation_email(invitation, created_by)
            channels['email'] = {'ok': ok, 'error': err}
            if ok:
                invitation.email_sent_at = timezone.now()

        if send_sms:
            ok, err = cls._send_invitation_sms(invitation)
            channels['sms'] = {'ok': ok, 'error': err}
            if ok:
                invitation.sms_sent_at = timezone.now()

        invitation.save(update_fields=['email_sent_at', 'sms_sent_at'])

        any_ok = any(c['ok'] for c in channels.values())

        if not any_ok:
            # Both channels failed — invitation is useless, remove it.
            invitation.delete()
            failures = '; '.join(
                f"{name}: {c['error'] or 'unknown error'}"
                for name, c in channels.items()
                if not c['ok']
            )
            return False, {
                'error': f'Invitation could not be delivered. {failures}',
                'code': 'DELIVERY_FAILED',
                'channels': channels,
            }

        # Log the invitation
        AuditService.log_admin_invitation_sent(
            created_by=created_by,
            email=email,
            invitation_id=str(invitation.id),
            request=request
        )

        logger.info(
            "Invitation to %s by %s — email_ok=%s sms_ok=%s",
            email, created_by.email, channels['email']['ok'], channels['sms']['ok'],
        )

        # Build a human-friendly summary for the toast.
        sent_bits = [n for n, c in channels.items() if c['ok']]
        failed_bits = [n for n, c in channels.items() if not c['ok']]
        summary = f"Invitation sent to {email} via {', '.join(sent_bits)}."
        if failed_bits:
            summary += f" Failed: {', '.join(failed_bits)}."

        # In-dashboard notification for the chief — surfaces in the bell
        # icon. Includes per-channel status so the chief can see at a
        # glance which channel needs a resend.
        cls._notify_chief_invitation_sent(
            created_by=created_by,
            invitation=invitation,
            sent_bits=sent_bits,
            failed_bits=failed_bits,
        )

        # Email confirmation to the chief so they have an out-of-app paper
        # trail of what was dispatched, on which channels, and when it
        # expires. Best-effort: any failure here must not block the
        # already-completed in-app success path.
        cls._send_chief_confirmation_email(
            inviter=created_by,
            invitation=invitation,
            sent_bits=sent_bits,
            failed_bits=failed_bits,
        )

        return True, {
            'success': True,
            'message': summary,
            'invitation_id': invitation.id,
            'expires_at': invitation.expires_at.isoformat(),
            'channels': channels,
        }

    # =====================================================================
    # RESEND (one channel only)
    # =====================================================================
    @classmethod
    def resend(
            cls,
            invitation_id: int,
            channel: str,
            request=None,
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Re-send a pending invitation via a single channel.

        Args:
            invitation_id: PK of the AdminInvitation row
            channel: 'email' or 'sms'

        Returns:
            Tuple: (success, response_data)
        """
        if channel not in {'email', 'sms'}:
            return False, {
                'error': f'Unknown channel "{channel}". Use "email" or "sms".',
                'code': 'INVALID_CHANNEL',
            }

        try:
            invitation = AdminInvitation.objects.get(id=invitation_id)
        except AdminInvitation.DoesNotExist:
            return False, {
                'error': 'Invitation not found.',
                'code': 'INVITATION_NOT_FOUND',
            }

        if invitation.is_accepted:
            return False, {
                'error': 'This invitation has already been accepted.',
                'code': 'INVITATION_USED',
            }

        if invitation.is_expired():
            return False, {
                'error': 'This invitation has expired.',
                'code': 'INVITATION_EXPIRED',
            }

        if channel == 'email':
            ok, err = cls._send_invitation_email(invitation, invitation.created_by)
            if ok:
                invitation.email_sent_at = timezone.now()
                invitation.save(update_fields=['email_sent_at'])

            AuditService.log_action(
                user=request.user if request and request.user.is_authenticated else None,
                action='ADMIN_INVITATION_SENT',
                entity_type='AdminInvitation',
                entity_id=str(invitation.id),
                details={
                    'email': invitation.email,
                    'resend': True,
                    'channel': 'email',
                    'ok': ok,
                },
                request=request,
            )

            cls._notify_chief_invitation_resent(
                created_by=request.user if request and request.user.is_authenticated else None,
                invitation=invitation,
                channel='email',
                ok=ok,
            )

            return ok, {
                'ok': ok,
                'error': err,
                'channel': 'email',
                'sent_at': invitation.email_sent_at.isoformat() if ok else None,
                'message': 'Email re-sent.' if ok else (err or 'Email failed.'),
            }

        # channel == 'sms'
        if not invitation.phone:
            return False, {
                'error': 'No phone on this invitation — SMS not possible.',
                'code': 'NO_PHONE',
            }
        ok, err = cls._send_invitation_sms(invitation)
        if ok:
            invitation.sms_sent_at = timezone.now()
            invitation.save(update_fields=['sms_sent_at'])

        cls._notify_chief_invitation_resent(
            created_by=request.user if request and request.user.is_authenticated else None,
            invitation=invitation,
            channel='sms',
            ok=ok,
        )

        return ok, {
            'ok': ok,
            'error': err,
            'channel': 'sms',
            'sent_at': invitation.sms_sent_at.isoformat() if ok else None,
            'message': 'SMS re-sent.' if ok else (err or 'SMS failed.'),
        }

    # =====================================================================
    # CHANNEL SENDERS (private)
    # =====================================================================
    @classmethod
    def _send_invitation_email(cls, invitation: AdminInvitation, created_by: User) -> Tuple[bool, Optional[str]]:
        """
        Send invitation email with HTML template.

        Returns:
            (ok, error_message)
        """
        from notifications.services.email_service import EmailService

        site_url = getattr(settings, 'BASE_URL', 'http://localhost:8000')
        invitation_link = f"{site_url}/accept-invite/{invitation.token}/"

        # Look up human-readable labels for the permissions we granted
        # so the invitee sees a friendly list, not raw keys.
        permissions_list = []
        try:
            from accounts.services.permission_service import PermissionService
            available = {p['key']: p for p in PermissionService.get_available_permissions()}
            for key in (invitation.permissions_json or {}).keys():
                meta = available.get(key)
                if meta:
                    permissions_list.append((key, meta.get('label', key)))
        except Exception:
            # Permissions are informational only — never break the email.
            pass

        subject = (
            f"You're invited to administer {getattr(settings, 'APP_NAME', 'Caldan Construction and Consultancy Firm')}"
        )

        context = {
            'invitation': invitation,
            'created_by': created_by,
            'invitation_link': invitation_link,
            'expires_at': invitation.expires_at,
            'expiry_hours': cls.INVITATION_EXPIRY_HOURS,
            'site_name': getattr(settings, 'APP_NAME', 'Caldan Construction and Consultancy Firm'),
            'support_email': getattr(settings, 'ADMIN_EMAIL', 'info.caldanconstruction@gmail.com'),
            'permissions': permissions_list,
            'temp_password': invitation.temp_password or '',
        }

        ok = EmailService.send_template(
            to_email=invitation.email,
            subject=subject,
            template_name='email/admin_invitation.html',
            context=context,
            email_type='ADMIN_INVITATION'
        )
        return (ok, None if ok else 'Email service failed to send.')

    @classmethod
    def _send_invitation_sms(cls, invitation: AdminInvitation) -> Tuple[bool, Optional[str]]:
        """
        Send invitation SMS.

        Returns:
            (ok, error_message)
        """
        from notifications.services.sms_service import SMSService

        if not invitation.phone:
            return False, 'No phone number on this invitation.'

        site_url = getattr(settings, 'BASE_URL', 'http://localhost:8000')
        invitation_link = f"{site_url}/accept-invite/{invitation.token}/"

        # Keep SMS short — Kenyan telco single-SMS limit is ~160 chars,
        # we send one segment.
        message = (
            f"Caldan: {invitation.created_by.full_name or 'An admin'} invited "
            f"you to be an admin. Accept here: {invitation_link} "
            f"(expires in {cls.INVITATION_EXPIRY_HOURS}h)"
        )

        ok = SMSService.send(
            phone_number=invitation.phone,
            message=message,
            user=invitation.created_by,
            notification_type='ADMIN_INVITATION',
        )
        return (ok, None if ok else 'SMS service failed to send.')

    # =====================================================================
    # CHIEF EMAIL — confirmation to the inviter when an invitation goes out.
    # =====================================================================
    @classmethod
    def _send_chief_confirmation_email(
            cls,
            inviter: User,
            invitation: AdminInvitation,
            sent_bits: list,
            failed_bits: list,
    ) -> None:
        """
        Send a confirmation email to the admin who sent the invitation.
        This is in addition to the in-dashboard notification and the
        invitee's email — it gives the inviter a paper trail of who
        they invited, when, and via which channels.

        Also sends a copy to settings.ADMIN_EMAIL if that's different
        from the inviter — so the operator inbox always has a paper
        trail of every admin invitation regardless of who sent it.
        """
        try:
            from notifications.services.email_service import EmailService

            channels_sent = ', '.join(sent_bits) if sent_bits else 'none'
            channels_failed = ', '.join(failed_bits) if failed_bits else ''
            base_context = {
                'invitation': invitation,
                'inviter': inviter,
                'site_name': getattr(settings, 'APP_NAME', 'Caldan Construction and Consultancy Firm'),
                'channels_sent': sent_bits,
                'channels_failed': failed_bits,
                'expiry_hours': cls.INVITATION_EXPIRY_HOURS,
                'invitation_url': f"{getattr(settings, 'BASE_URL', 'http://localhost:8000')}/accept-invite/{invitation.token}/",
                'manage_url': f"{getattr(settings, 'BASE_URL', 'http://localhost:8000')}/admins/",
            }
            subject = (
                f"Invitation sent to {invitation.email} "
                f"— {('via ' + channels_sent) if sent_bits else 'all channels failed'}"
            )

            def _send(recipient: str) -> bool:
                return EmailService.send_template(
                    to_email=recipient,
                    subject=subject,
                    template_name='email/admin_invitation_sent.html',
                    context=base_context,
                    email_type='ADMIN_INVITATION_SENT',
                )

            # 1. The inviter (chief) always gets a copy
            _send(inviter.email)

            # 2. The operator inbox (ADMIN_EMAIL) gets a copy too — unless
            #    the inviter is already that account.
            admin_email = getattr(settings, 'ADMIN_EMAIL', '') or ''
            if admin_email and admin_email.lower() != inviter.email.lower():
                _send(admin_email)

        except Exception as exc:
            # Confirmation email is best-effort — never break the send flow.
            logger.warning(
                "Exception while sending chief confirmation email for invitation %s: %s",
                invitation.id, exc,
            )

    # =====================================================================
    # IN-DASHBOARD NOTIFICATIONS
    # =====================================================================
    @classmethod
    def _notify_chief_invitation_sent(
            cls,
            created_by: User,
            invitation: AdminInvitation,
            sent_bits: list,
            failed_bits: list,
    ) -> None:
        """
        Drop a Notification row into the chief's dashboard so the bell
        icon surfaces a confirmation alongside the email delivery.
        Per-channel status is included so the chief knows which channel
        (if any) needs a resend.
        """
        try:
            from notifications.services.notification_service import NotificationService
            from django.urls import reverse

            channels_text = ', '.join(sent_bits) if sent_bits else 'none'
            if failed_bits:
                channels_text += f" (failed: {', '.join(failed_bits)})"

            title = f"Invitation sent to {invitation.email}"
            message = (
                f"{invitation.full_name or invitation.email} has been invited to be "
                f"a {invitation.role or 'PLATFORM_ADMIN'}. Delivered via {channels_text}."
            )

            NotificationService.create(
                user=created_by,
                title=title,
                message=message,
                notification_type='ADMIN_INVITATION',
                priority='HIGH' if failed_bits else 'MEDIUM',
                icon='fa-user-plus',
                action_url=reverse('accounts:admin_list'),
                metadata={
                    'invitation_id': invitation.id,
                    'invitee_email': invitation.email,
                    'channels_sent': sent_bits,
                    'channels_failed': failed_bits,
                },
            )
        except Exception as exc:
            # Notifications are best-effort — never break the send flow.
            logger.warning(
                "Failed to create in-dashboard notification for invitation %s: %s",
                invitation.id, exc,
            )

    @classmethod
    def _notify_chief_invitation_resent(
            cls,
            created_by: Optional[User],
            invitation: AdminInvitation,
            channel: str,
            ok: bool,
    ) -> None:
        """In-dashboard notification on a Resend action."""
        if not created_by:
            return
        try:
            from notifications.services.notification_service import NotificationService
            from django.urls import reverse

            verb = "resent" if ok else "failed to resend"
            title = f"Invitation {channel.upper()} {verb}"
            message = (
                f"{channel.upper()} {verb} for {invitation.email}."
            )

            NotificationService.create(
                user=created_by,
                title=title,
                message=message,
                notification_type='ADMIN_INVITATION',
                priority='MEDIUM',
                icon='fa-paper-plane' if ok else 'fa-exclamation-triangle',
                action_url=reverse('accounts:admin_list'),
                metadata={
                    'invitation_id': invitation.id,
                    'channel': channel,
                    'ok': ok,
                    'resend': True,
                },
            )
        except Exception as exc:
            logger.warning(
                "Failed to create resend notification for invitation %s: %s",
                invitation.id, exc,
            )

    # =====================================================================
    # TEMPORARY PASSWORD GENERATION
    # =====================================================================
    TEMP_PASSWORD_LENGTH = 12
    # Confusable characters removed (0/O, 1/l/I, etc.) for readability.
    _TEMP_ALPHABET = (
        'ABCDEFGHJKLMNPQRSTUVWXYZ'    # uppercase, no I/O
        'abcdefghjkmnpqrstuvwxyz'     # lowercase, no i/l/o
        '23456789'                     # digits, no 0/1
    )

    @classmethod
    def _generate_temporary_password(cls) -> str:
        """
        Generate a single-use temporary password sent in the invitation
        email. Length is fixed at 12 with one of each: upper, lower, digit.
        The invitee is required to change it on first login via the
        force-change-password modal.
        """
        length = cls.TEMP_PASSWORD_LENGTH
        # Always one character from each group so strength check passes.
        upper = secrets.choice(cls._TEMP_ALPHABET[:24])  # A-Z minus I/O
        lower = secrets.choice(cls._TEMP_ALPHABET[24:48])  # a-z minus i/l/o
        digit = secrets.choice(cls._TEMP_ALPHABET[48:])  # 2-9
        remaining = ''.join(
            secrets.choice(cls._TEMP_ALPHABET)
            for _ in range(length - 3)
        )
        chars = list(upper + lower + digit + remaining)
        # Fisher–Yates shuffle so the structural chars aren't always
        # in the same position.
        for i in range(len(chars) - 1, 0, -1):
            j = secrets.randbelow(i + 1)
            chars[i], chars[j] = chars[j], chars[i]
        return ''.join(chars)

    @classmethod
    def accept_invitation(
            cls,
            token: str,
            password: Optional[str],
            full_name: str,
            phone: str,
            request=None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Accept an invitation and create admin account.

        Args:
            token: Invitation token
            password: Optional. If omitted (None) the service uses the
                system-generated temporary password that was emailed
                to the invitee. The new account is created with
                ``password_change_required=True`` so the invitee MUST
                pick a real password the moment they sign in.
            full_name: Full name of the new admin
            phone: Phone number of the new admin
            request: Django request object

        Returns:
            Tuple: (success, response_data)
        """
        # Get invitation
        try:
            invitation = AdminInvitation.objects.get(token=token)
        except AdminInvitation.DoesNotExist:
            return False, {
                'error': 'Invalid invitation link',
                'code': 'INVALID_TOKEN'
            }

        # Check if invitation is valid
        if not invitation.is_valid():
            if invitation.is_expired():
                return False, {
                    'error': 'This invitation has expired. Please request a new one.',
                    'code': 'INVITATION_EXPIRED'
                }
            if invitation.is_accepted:
                return False, {
                    'error': 'This invitation has already been used.',
                    'code': 'INVITATION_USED'
                }
            return False, {
                'error': 'This invitation is no longer valid.',
                'code': 'INVITATION_INVALID'
            }

        # Check if email already used
        if User.objects.filter(email=invitation.email).exists():
            return False, {
                'error': 'A user with this email already exists',
                'code': 'USER_EXISTS'
            }

        # Resolve the password we'll seed the account with. Either the
        # invitee supplied one (legacy path), or we fall back to the
        # system-generated temp password that was emailed to them.
        if password:
            if len(password) < getattr(settings, 'PASSWORD_MIN_LENGTH', 8):
                return False, {
                    'error': f'Password must be at least {getattr(settings, "PASSWORD_MIN_LENGTH", 8)} characters',
                    'code': 'PASSWORD_TOO_SHORT'
                }
            initial_password = password
        else:
            if not invitation.temp_password:
                return False, {
                    'error': 'No temporary password on this invitation. '
                             'Please ask the admin who invited you to send a new one.',
                    'code': 'NO_TEMP_PASSWORD',
                }
            initial_password = invitation.temp_password

        # Create user
        try:
            with transaction.atomic():
                user = User.objects.create_platform_admin(
                    email=invitation.email,
                    password=initial_password,
                    full_name=full_name,
                    phone=phone,
                    is_active=True,
                    is_staff=True,
                    is_superuser=False,
                    is_chief=False,
                    password_change_required=True,  # Force password change on first login
                )

                # Apply the chief's permission choices as the authoritative set.
                # Anything the chief left unchecked is forced to False
                # so the new admin's sidebar reflects exactly what the
                # chief decided — granting 0 permissions produces a
                # near-empty sidebar (which is the expected behaviour).
                from accounts.services.permission_service import PermissionService
                granted = dict(invitation.permissions_json or {})
                PermissionService.set_user_permissions(user, granted, replace=True)

                # Mark invitation as accepted. The accept() helper clears
                # the temp_password so it never lingers in the DB after
                # the account has been claimed.
                invitation.accept(user)

                # Log the user creation
                AuditService.log_admin_invitation_accepted(
                    user=user,
                    invitation_id=str(invitation.id),
                    request=request
                )

                # Log user creation
                AuditService.log_user_created(
                    created_by=user,  # Self-creation via invitation
                    new_user=user,
                    request=request
                )

                logger.info(f"Admin account created via invitation: {user.email}")

                return True, {
                    'success': True,
                    'message': 'Account created successfully. Please login.',
                    'redirect_url': 'accounts:login'
                }

        except Exception as e:
            logger.error(f"Failed to create admin account: {str(e)}")
            return False, {
                'error': 'Failed to create account. Please try again.',
                'code': 'ACCOUNT_CREATION_FAILED'
            }

    @classmethod
    def get_invitation_status(cls, token: str) -> Dict[str, Any]:
        """
        Get status of an invitation.

        Args:
            token: Invitation token

        Returns:
            dict: Invitation status information
        """
        try:
            invitation = AdminInvitation.objects.get(token=token)
        except AdminInvitation.DoesNotExist:
            return {
                'valid': False,
                'error': 'Invalid invitation link',
                'code': 'INVALID_TOKEN'
            }

        # `created_by` may be None (deleted user) or — if the user was
        # hard-deleted — its `.full_name` access may raise. Always serialize
        # it as a dict so the template can safely access fields.
        cb = invitation.created_by
        if cb is not None:
            created_by_info = {
                'id': cb.id,
                'full_name': cb.full_name or '',
                'email': cb.email or '',
            }
        else:
            created_by_info = None

        status = {
            'valid': invitation.is_valid(),
            'email': invitation.email,
            'created_at': invitation.created_at.isoformat(),
            'expires_at': invitation.expires_at.isoformat(),
            'created_by': created_by_info,
            'is_accepted': invitation.is_accepted,
            # Recruitment details collected up-front so the acceptance
            # page can pre-fill the form (and the chief can see who
            # they invited without leaving the dashboard).
            'full_name': invitation.full_name or '',
            'phone': invitation.phone or '',
            'role': invitation.role or '',
            'permissions': invitation.permissions_json or {},
            'personal_message': invitation.personal_message or '',
            'email_sent_at': invitation.email_sent_at.isoformat() if invitation.email_sent_at else None,
            'sms_sent_at': invitation.sms_sent_at.isoformat() if invitation.sms_sent_at else None,
        }

        if invitation.is_accepted:
            status['accepted_at'] = invitation.accepted_at.isoformat()

        if invitation.is_expired():
            status['error'] = 'This invitation has expired'
            status['code'] = 'INVITATION_EXPIRED'

        return status

    @classmethod
    def get_pending_invitations(cls) -> list:
        """
        Get all pending (valid) invitations.

        Returns:
            list: List of pending AdminInvitation objects
        """
        return list(AdminInvitation.objects.filter(
            is_accepted=False,
            expires_at__gt=timezone.now()
        ).order_by('-created_at'))

    @classmethod
    def get_invitations_by_email(cls, email: str) -> list:
        """
        Get all invitations for a specific email.

        Args:
            email: Email address to search for

        Returns:
            list: List of AdminInvitation objects
        """
        return list(AdminInvitation.objects.filter(
            email=email
        ).order_by('-created_at'))

    @classmethod
    def cleanup_expired_invitations(cls) -> int:
        """
        Delete expired invitations.

        Returns:
            int: Number of invitations deleted
        """
        expired = AdminInvitation.objects.filter(
            is_accepted=False,
            expires_at__lt=timezone.now()
        )
        count = expired.count()
        expired.delete()

        if count > 0:
            logger.info(f"Cleaned up {count} expired invitations")

        return count