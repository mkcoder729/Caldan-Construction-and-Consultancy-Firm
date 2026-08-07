"""
OTP Service - 8-digit OTP generation and verification with SHA-256 hashing.

This service handles all OTP operations including generation, verification,
and resend management for the Caldan Construction platform.
"""

import logging
import hashlib
import secrets
from typing import Tuple, Optional
from django.utils import timezone
from django.conf import settings
from django.core.cache import cache

from accounts.models import User

logger = logging.getLogger('caldan')


class OTPService:
    """
    OTP service for 8-digit code generation and verification.

    Features:
    - 8-digit cryptographically secure OTP generation
    - SHA-256 hashing (plain text never stored)
    - 5-minute expiry
    - 3 attempt limit with cooldown
    - Resend with cooldown and hourly limit
    """

    OTP_LENGTH = 8
    OTP_EXPIRY_MINUTES = 5
    MAX_ATTEMPTS = 3
    RESEND_COOLDOWN_SECONDS = 60
    MAX_RESENDS_PER_HOUR = 5

    @classmethod
    def generate_otp(cls, user: User) -> str:
        """
        Generate an 8-digit OTP and store its SHA-256 hash.

        Args:
            user: User to generate OTP for

        Returns:
            str: The plaintext 8-digit OTP code
        """
        # Get settings with fallbacks
        otp_length = getattr(settings, 'OTP_LENGTH', cls.OTP_LENGTH)

        # Generate cryptographically secure 8-digit OTP
        otp_code = ''.join([str(secrets.randbelow(10)) for _ in range(otp_length)])

        # Hash and store
        user.otp_code_hash = hashlib.sha256(otp_code.encode()).hexdigest()
        user.otp_created_at = timezone.now()
        user.otp_attempts = 0
        user.save(update_fields=['otp_code_hash', 'otp_created_at', 'otp_attempts'])

        # Log OTP generation
        logger.info(f"OTP generated for user: {user.email}")

        return otp_code

    @classmethod
    def verify_otp(cls, user: User, otp_code: str) -> Tuple[bool, str]:
        """
        Verify an OTP code against the stored hash.

        Args:
            user: User to verify OTP for
            otp_code: The 8-digit OTP code to verify

        Returns:
            Tuple: (success, message)
        """
        # Get settings with fallbacks
        expiry_minutes = getattr(settings, 'OTP_EXPIRY_MINUTES', cls.OTP_EXPIRY_MINUTES)
        max_attempts = getattr(settings, 'OTP_MAX_ATTEMPTS', cls.MAX_ATTEMPTS)

        # Check if OTP exists
        if not user.otp_code_hash:
            return False, "No OTP generated. Please request a new code."

        # Check if OTP is expired
        if not user.otp_created_at:
            return False, "No OTP generated. Please request a new code."

        expiry_time = user.otp_created_at + timezone.timedelta(minutes=expiry_minutes)
        if timezone.now() > expiry_time:
            # Clear expired OTP
            user.clear_otp()
            return False, "OTP has expired. Please request a new code."

        # Check attempt limit
        if user.otp_attempts >= max_attempts:
            # Clear OTP after max attempts
            user.clear_otp()
            return False, "Too many failed attempts. Please request a new code."

        # Verify the code
        hashed_code = hashlib.sha256(otp_code.encode()).hexdigest()

        if hashed_code == user.otp_code_hash:
            # Success - clear OTP and mark email verified
            user.clear_otp()
            user.is_email_verified = True
            user.save(update_fields=['otp_code_hash', 'otp_created_at', 'otp_attempts', 'is_email_verified'])

            logger.info(f"OTP verified successfully for user: {user.email}")
            return True, "OTP verified successfully"

        # Failed attempt
        user.otp_attempts += 1
        user.save(update_fields=['otp_attempts'])

        remaining = max_attempts - user.otp_attempts

        logger.warning(f"OTP verification failed for user: {user.email}. {remaining} attempts remaining.")

        if remaining <= 0:
            return False, "Too many failed attempts. Please request a new code."

        return False, f"Invalid OTP. {remaining} attempt(s) remaining."

    @classmethod
    def verify_otp_with_cache(cls, user: User, otp_code: str) -> Tuple[bool, str]:
        """
        Verify OTP with rate limiting via cache.

        This method adds an additional layer of rate limiting using Redis cache
        to prevent brute force attacks across multiple users.

        Args:
            user: User to verify OTP for
            otp_code: The 8-digit OTP code to verify

        Returns:
            Tuple: (success, message)
        """
        # Rate limit check using cache
        cache_key = f"otp_rate_limit_{user.email}"
        attempts = cache.get(cache_key, 0)

        if attempts >= 10:  # 10 attempts per 5 minutes globally
            return False, "Too many verification attempts. Please try again in 5 minutes."

        # Verify OTP
        success, message = cls.verify_otp(user, otp_code)

        # Increment rate limit counter if failed
        if not success and "Invalid OTP" in message:
            cache.set(cache_key, attempts + 1, 300)  # 5 minute expiry

        return success, message

    @classmethod
    def validate_otp_code(cls, otp_code: str) -> bool:
        """
        Validate OTP code format.

        Args:
            otp_code: OTP code to validate

        Returns:
            bool: True if valid format
        """
        if not otp_code:
            return False

        if len(otp_code) != cls.OTP_LENGTH:
            return False

        if not otp_code.isdigit():
            return False

        return True

    @classmethod
    def get_otp_status(cls, user: User) -> dict:
        """
        Get OTP status for a user.

        Args:
            user: User to get OTP status for

        Returns:
            dict: OTP status information
        """
        status = {
            'has_otp': bool(user.otp_code_hash),
            'attempts_used': user.otp_attempts,
            'max_attempts': getattr(settings, 'OTP_MAX_ATTEMPTS', cls.MAX_ATTEMPTS),
            'is_email_verified': user.is_email_verified,
        }

        if user.otp_created_at:
            expiry_minutes = getattr(settings, 'OTP_EXPIRY_MINUTES', cls.OTP_EXPIRY_MINUTES)
            expiry_time = user.otp_created_at + timezone.timedelta(minutes=expiry_minutes)
            status['expires_at'] = expiry_time.isoformat()
            status['is_expired'] = timezone.now() > expiry_time
            status['remaining_seconds'] = max(0, (expiry_time - timezone.now()).total_seconds())

        return status

    @classmethod
    def clear_otp(cls, user: User) -> None:
        """
        Clear OTP for a user.

        Args:
            user: User to clear OTP for
        """
        user.clear_otp()
        logger.info(f"OTP cleared for user: {user.email}")

    @classmethod
    def can_resend_otp(cls, user: User) -> Tuple[bool, str, int]:
        """
        Check if user can request a new OTP.

        Args:
            user: User to check

        Returns:
            Tuple: (can_resend, message, wait_seconds)
        """
        # Check if OTP exists and is still valid
        if user.otp_code_hash and user.otp_created_at:
            expiry_minutes = getattr(settings, 'OTP_EXPIRY_MINUTES', cls.OTP_EXPIRY_MINUTES)
            expiry_time = user.otp_created_at + timezone.timedelta(minutes=expiry_minutes)

            if timezone.now() <= expiry_time:
                # OTP is still valid
                remaining_seconds = max(0, (expiry_time - timezone.now()).total_seconds())
                return False, "Current OTP is still valid", int(remaining_seconds)

        # Check cooldown
        cooldown = getattr(settings, 'OTP_RESEND_COOLDOWN_SECONDS', cls.RESEND_COOLDOWN_SECONDS)
        if user.otp_last_resend:
            elapsed = (timezone.now() - user.otp_last_resend).total_seconds()
            if elapsed < cooldown:
                wait = int(cooldown - elapsed)
                return False, f"Please wait {wait} seconds before requesting a new code", wait

        # Check hourly limit
        max_resends = getattr(settings, 'OTP_MAX_RESENDS_PER_HOUR', cls.MAX_RESENDS_PER_HOUR)
        if user.otp_resend_count >= max_resends:
            return False, "Maximum OTP requests per hour exceeded. Please try again later.", 0

        return True, "You can request a new OTP", 0