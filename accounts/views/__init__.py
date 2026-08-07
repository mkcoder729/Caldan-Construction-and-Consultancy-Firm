# Accounts Views - Caldan Construction
# "Building Kenya's Future, One Project at a Time."

from accounts.views._auth_views import (
    LoginView,
    OTPVerifyView,
    LogoutView,
    LogoutAllView,
    ResendOTPView,
    AccountLockedView,
)
from accounts.views._setup_views import SetupView, SetupCompleteView, SetupInvalidView
from accounts.views._invitation_views import AcceptInvitationView, InvitationStatusView
from accounts.views._admin_views import (
    AdminListView,
    AdminDetailView,
    AdminDeleteView,
    AdminPermissionsView,
    AdminInviteView,
    AdminLockView,
    AdminUnlockView,
    AdminEditView,
    AdminInvitationResendView,
)
from accounts.views._profile_views import ProfileView, ProfileUpdateView
from accounts.views._password_views import ChangePasswordView

__all__ = [
    # Auth
    'LoginView',
    'OTPVerifyView',
    'LogoutView',
    'LogoutAllView',
    'ResendOTPView',
    'AccountLockedView',
    # Setup
    'SetupView',
    'SetupCompleteView',
    'SetupInvalidView',
    # Invitation
    'AcceptInvitationView',
    'InvitationStatusView',
    # Admin Management
    'AdminListView',
    'AdminDetailView',
    'AdminDeleteView',
    'AdminPermissionsView',
    'AdminInviteView',
    'AdminLockView',
    'AdminUnlockView',
    'AdminEditView',
    'AdminInvitationResendView',
    # Profile
    'ProfileView',
    'ProfileUpdateView',
    # Password
    'ChangePasswordView',
]