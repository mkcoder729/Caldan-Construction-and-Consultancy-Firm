"""
URL Configuration for the accounts app.
"""

from django.urls import path, reverse_lazy
from django.contrib.auth import views as auth_views

from accounts.views import (
    SetupView,
    SetupCompleteView,
    SetupInvalidView,
    LoginView,
    OTPVerifyView,
    LogoutView,
    LogoutAllView,
    ResendOTPView,
    AccountLockedView,
    AcceptInvitationView,
    InvitationStatusView,
    ProfileView,
    ProfileUpdateView,
    ChangePasswordView,
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

app_name = 'accounts'

urlpatterns = [
    # =====================================================================
    # SETUP URLs - Root level for first-time setup
    # Flow: GET /setup/ (form) → POST /setup/ → /setup-complete/ (success)
    # Once a Chief Admin exists, GET /setup/ renders /setup/invalid/ inline.
    # =====================================================================
    path('setup/', SetupView.as_view(), name='setup'),
    path('setup-complete/', SetupCompleteView.as_view(), name='setup_complete'),
    path('setup/invalid/', SetupInvalidView.as_view(), name='setup_invalid'),

    # =====================================================================
    # AUTHENTICATION URLs - Root level for easy access
    # =====================================================================
    path('login/', LoginView.as_view(), name='login'),
    path('verify-otp/', OTPVerifyView.as_view(), name='otp_verify'),
    path('resend-otp/', ResendOTPView.as_view(), name='resend_otp'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('logout-all/', LogoutAllView.as_view(), name='logout_all'),
    path('account-locked/', AccountLockedView.as_view(), name='account_locked'),

    # =====================================================================
    # PASSWORD RESET URLs
    # =====================================================================
    path('password-reset/',
         auth_views.PasswordResetView.as_view(
             template_name='accounts/shared/password_reset.html',
             email_template_name='email/password_reset.html',
             subject_template_name='email/password_reset_subject.txt',
             success_url=reverse_lazy('accounts:password_reset_done'),
             extra_email_context={
                 'brand_name': 'Caldan Construction and Consultancy Firm',
                 'tagline': "Building Kenya's Future, One Project at a Time.",
                 'support_email': 'info.caldanconstruction@gmail.com',
                 'site_url': 'http://localhost:8000',
             },
         ),
         name='password_reset'),
    path('password-reset-done/',
         auth_views.PasswordResetDoneView.as_view(
             template_name='accounts/shared/password_reset_done.html',
         ),
         name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/',
         auth_views.PasswordResetConfirmView.as_view(
             template_name='accounts/shared/password_reset_confirm.html',
             success_url=reverse_lazy('accounts:password_reset_complete'),
         ),
         name='password_reset_confirm'),
    path('password-reset-complete/',
         auth_views.PasswordResetCompleteView.as_view(
             template_name='accounts/shared/password_reset_complete.html',
         ),
         name='password_reset_complete'),

    # =====================================================================
    # INVITATION URLs
    # =====================================================================
    path('accept-invite/<str:token>/', AcceptInvitationView.as_view(), name='accept_invite'),
    path('invite-status/<str:token>/', InvitationStatusView.as_view(), name='invite_status'),

    # =====================================================================
    # PROFILE URLs
    # =====================================================================
    path('profile/', ProfileView.as_view(), name='profile'),
    path('profile/edit/', ProfileUpdateView.as_view(), name='profile_edit'),
    path('change-password/', ChangePasswordView.as_view(), name='change_password'),

    # =====================================================================
    # ADMIN MANAGEMENT URLs (Chief Admin only)
    # =====================================================================
    path('admins/', AdminListView.as_view(), name='admin_list'),
    path('admins/invite/', AdminInviteView.as_view(), name='admin_invite'),
    path('admins/<int:admin_id>/', AdminDetailView.as_view(), name='admin_detail'),
    path('admins/<int:admin_id>/edit/', AdminEditView.as_view(), name='admin_edit'),
    path('admins/<int:admin_id>/delete/', AdminDeleteView.as_view(), name='admin_delete'),
    path('admins/<int:admin_id>/permissions/', AdminPermissionsView.as_view(), name='admin_permissions'),
    path('admins/<int:admin_id>/lock/', AdminLockView.as_view(), name='admin_lock'),
    path('admins/<int:admin_id>/unlock/', AdminUnlockView.as_view(), name='admin_unlock'),

    # Resend an existing pending invitation via a single channel.
    # This sits BELOW the admin_id routes so 'invitations' can't be
    # parsed as an int — Django wouldn't match it anyway, but the
    # explicit prefix keeps intent obvious.
    path(
        'admins/invitations/<int:invitation_id>/resend/<str:channel>/',
        AdminInvitationResendView.as_view(),
        name='admin_invitation_resend',
    ),
]