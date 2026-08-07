"""
Accounts app for Caldan Construction.
Handles authentication, authorization, OTP, audit logging, and user management.

This app provides the security backbone for the entire platform including:
- Custom User model with email-based authentication
- 8-digit OTP with SHA-256 hashing
- Role-based access control (Chief Admin, Platform Admin, Client)
- Immutable audit logging with SHA-256 hash chain
- Secure admin invitations with 48-hour expiry
- Trusted devices for "Remember Me" functionality
- Account lockout on failed login attempts
"""

__version__ = '1.0.0'
__app_name__ = 'accounts'
__description__ = 'Authentication & Authorization for Caldan Construction and Consultancy Firm'