"""
Admin Views - Manage platform admins.

This module handles admin management including listing, viewing,
deleting, locking/unlocking, and managing permissions for platform admins.
"""

import logging
from datetime import timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views import View
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect

from accounts.models import User, AdminInvitation
from accounts.models.audit import AuditLog
from accounts.forms.invitation_form import InviteAdminForm, InvitationDetailsAdminForm
from accounts.forms.admin_edit_form import AdminEditForm
from accounts.services.permission_service import PermissionService
from accounts.services.invitation_service import InvitationService
from accounts.services.audit_service import AuditService

logger = logging.getLogger('caldan')


@method_decorator(login_required, name='dispatch')
class AdminListView(View):
    """
    The chief admin's "Manage Admins" console — one page that lists every
    platform admin, their state, pending invitations, and offers row-level
    actions (view / edit / lock / unlock / edit permissions / delete).

    The 2-step invite flow lives on its own dedicated page at
    ``/admins/invite/`` (see AdminInviteView). The hero on this console
    links to it. Keeping the two pages separate means the console stays
    focused on management actions — and the invite page gets to be a
    dedicated, polished experience.
    """

    def get(self, request):
        if not request.user.is_admin:
            messages.error(request, 'Access denied. Admin privileges required.')
            return redirect('dashboard:overview')

        admins = list(User.objects.filter(
            role__in=[User.Role.CHIEF_ADMIN, User.Role.PLATFORM_ADMIN]
        ).order_by('-is_chief', '-date_joined'))

        now = timezone.now()
        for a in admins:
            a.is_currently_locked = bool(
                a.locked_until and a.locked_until > now
            )
            a.permissions = PermissionService.get_user_permissions(a)

        paginator = Paginator(admins, 20)
        page = request.GET.get('page', 1)
        admins_page = paginator.get_page(page)

        if request.user.is_chief:
            pending_invitations = InvitationService.get_pending_invitations()
        else:
            pending_invitations = [
                inv for inv in InvitationService.get_pending_invitations()
                if inv.created_by_id == request.user.id
            ]

        locked_count = sum(1 for a in admins if a.is_currently_locked)
        active_count = sum(
            1 for a in admins
            if a.is_active and not a.is_currently_locked
        )
        chief_count = sum(1 for a in admins if a.is_chief)

        can_invite = PermissionService.has_permission(request.user, 'can_invite_admins')

        return render(request, 'accounts/dashboard/admin/manage_admins.html', {
            'admins': admins_page,
            'pending_invitations': pending_invitations,
            'can_invite': can_invite,
            'can_delete': (
                request.user.is_chief and
                PermissionService.has_permission(request.user, 'can_delete_data')
            ),
            'can_edit_permissions': request.user.is_chief,
            'can_lock': request.user.is_chief,
            'stats': {
                'total': len(admins),
                'chief': chief_count,
                'active': active_count,
                'locked': locked_count,
            },
            'page_title': 'Manage Admins - Caldan Construction and Consultancy Firm',
        })


@method_decorator(login_required, name='dispatch')
class AdminDetailView(View):
    """
    View admin details.
    """

    def get(self, request, admin_id):
        """
        Display admin details.
        """
        # Only admins can view this
        if not request.user.is_admin:
            messages.error(request, 'Access denied. Admin privileges required.')
            return redirect('dashboard:overview')

        admin = get_object_or_404(
            User,
            id=admin_id,
            role__in=[User.Role.CHIEF_ADMIN, User.Role.PLATFORM_ADMIN]
        )

        # Get permissions
        permissions = PermissionService.get_user_permissions(admin)

        context = {
            'admin': admin,
            'permissions': permissions,
            'can_edit_permissions': (
                    request.user.is_chief and
                    not admin.is_chief and
                    PermissionService.has_permission(request.user, 'can_manage_settings')
            ),
            'page_title': f'Admin Details - {admin.full_name}',
        }
        return render(request, 'accounts/dashboard/admin/admin_detail.html', context)


@method_decorator(login_required, name='dispatch')
class AdminDeleteView(View):
    """
    Delete a platform admin.
    """

    def post(self, request, admin_id):
        """
        Process admin deletion.
        """
        # Only admins with delete permission can delete
        if not PermissionService.has_permission(request.user, 'can_delete_data'):
            messages.error(request, 'You do not have permission to delete admins.')
            return redirect('accounts:admin_list')

        admin = get_object_or_404(
            User,
            id=admin_id,
            role__in=[User.Role.CHIEF_ADMIN, User.Role.PLATFORM_ADMIN]
        )

        # Prevent self-deletion
        if admin.id == request.user.id:
            messages.error(request, 'You cannot delete your own account.')
            return redirect('accounts:admin_list')

        # Prevent Chief Admin deletion
        if admin.is_chief:
            messages.error(request, 'Cannot delete Chief Admin account.')
            return redirect('accounts:admin_list')

        # Store admin info for audit
        admin_email = admin.email
        admin_name = admin.full_name
        admin_role = admin.role

        # Delete the admin
        admin.delete()

        # Log deletion
        AuditService.log_user_deleted(
            deleted_by=request.user,
            deleted_user=admin,
            request=request
        )

        messages.success(request, f'Admin {admin_name} has been deleted.')
        logger.info(f"Admin {admin_email} deleted by {request.user.email}")

        return redirect('accounts:admin_list')


@method_decorator(login_required, name='dispatch')
class AdminPermissionsView(View):
    """
    Edit admin permissions.
    """

    def get(self, request, admin_id):
        """
        Display permission edit form. Returns JSON when fetched via XHR.
        """
        # Only Chief Admin can edit permissions
        if not request.user.is_chief:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                from django.http import JsonResponse
                return JsonResponse({'error': 'Only Chief Admin can edit permissions.'}, status=403)
            messages.error(request, 'Only Chief Admin can edit permissions.')
            return redirect('accounts:admin_list')

        admin = get_object_or_404(
            User,
            id=admin_id,
            role__in=[User.Role.CHIEF_ADMIN, User.Role.PLATFORM_ADMIN]
        )

        # Prevent editing Chief Admin permissions
        if admin.is_chief:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                from django.http import JsonResponse
                return JsonResponse({'error': 'Cannot modify Chief Admin permissions.'}, status=400)
            messages.error(request, 'Cannot modify Chief Admin permissions.')
            return redirect('accounts:admin_list')

        # Get current permissions
        current_permissions = PermissionService.get_user_permissions(admin)
        available_permissions = PermissionService.get_available_permissions()

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            from django.http import JsonResponse
            return JsonResponse({
                'admin_id': admin.id,
                'admin_name': admin.full_name,
                'permissions': current_permissions,
                'available': available_permissions,
            })

        context = {
            'admin': admin,
            'current_permissions': current_permissions,
            'available_permissions': available_permissions,
            'page_title': f'Edit Permissions - {admin.full_name}',
        }
        return render(request, 'accounts/dashboard/admin/admin_permissions.html', context)

    def post(self, request, admin_id):
        """
        Process permission update.
        """
        # Only Chief Admin can edit permissions
        if not request.user.is_chief:
            messages.error(request, 'Only Chief Admin can edit permissions.')
            return redirect('accounts:admin_list')

        admin = get_object_or_404(
            User,
            id=admin_id,
            role__in=[User.Role.CHIEF_ADMIN, User.Role.PLATFORM_ADMIN]
        )

        # Prevent editing Chief Admin permissions
        if admin.is_chief:
            messages.error(request, 'Cannot modify Chief Admin permissions.')
            return redirect('accounts:admin_list')

        # Collect permissions from form
        permissions = {}
        available_permissions = PermissionService.get_available_permissions()

        for perm in available_permissions:
            key = perm['key']
            permissions[key] = request.POST.get(key) == 'on'

        # Save permissions
        PermissionService.set_user_permissions(admin, permissions)

        # Log permission change
        AuditService.log_action(
            user=request.user,
            action=AuditLog.Action.PERMISSION_CHANGED,
            entity_type='User',
            entity_id=admin.id,
            details={
                'admin': admin.email,
                'permissions': permissions,
            },
            request=request
        )

        messages.success(request, f'Permissions updated for {admin.full_name}.')
        logger.info(f"Permissions updated for {admin.email} by {request.user.email}")

        return redirect('accounts:admin_list')


@method_decorator(login_required, name='dispatch')
class AdminEditView(View):
    """
    Edit another admin's profile (full_name, phone, email, is_active).
    Chief Admin only. Cannot edit chief admins. Cannot self-edit email
    to break OTP/login.
    """

    def get(self, request, admin_id):
        if not request.user.is_chief:
            messages.error(request, 'Only the Chief Admin can edit admin accounts.')
            return redirect('accounts:admin_list')

        admin = get_object_or_404(
            User,
            id=admin_id,
            role__in=[User.Role.CHIEF_ADMIN, User.Role.PLATFORM_ADMIN]
        )

        form = AdminEditForm(instance=admin)
        context = {
            'admin': admin,
            'form': form,
            'page_title': f'Edit {admin.full_name} - Caldan',
            'permissions': PermissionService.get_user_permissions(admin),
            'is_currently_locked': bool(
                admin.locked_until and admin.locked_until > timezone.now()
            ),
        }
        return render(request, 'accounts/dashboard/admin/admin_edit.html', context)

    def post(self, request, admin_id):
        if not request.user.is_chief:
            messages.error(request, 'Only the Chief Admin can edit admin accounts.')
            return redirect('accounts:admin_list')

        admin = get_object_or_404(
            User,
            id=admin_id,
            role__in=[User.Role.CHIEF_ADMIN, User.Role.PLATFORM_ADMIN]
        )

        # Prevent editing chief admins for safety.
        if admin.is_chief and admin.id != request.user.id:
            messages.error(request, 'Cannot edit another Chief Admin.')
            return redirect('accounts:admin_list')

        form = AdminEditForm(request.POST, instance=admin)
        if form.is_valid():
            form.save()
            AuditService.log_action(
                user=request.user,
                action=AuditLog.Action.PROFILE_UPDATED,
                entity_type='User',
                entity_id=admin.id,
                details={
                    'admin_email': admin.email,
                    'fields_changed': list(form.changed_data),
                },
                request=request
            )
            messages.success(request, f'Admin {admin.full_name} updated.')
            logger.info(f"Admin {admin.email} edited by {request.user.email}")
            return redirect('accounts:admin_edit', admin_id=admin.id)

        context = {
            'admin': admin,
            'form': form,
            'page_title': f'Edit {admin.full_name} - Caldan',
            'permissions': PermissionService.get_user_permissions(admin),
            'is_currently_locked': bool(
                admin.locked_until and admin.locked_until > timezone.now()
            ),
        }
        return render(request, 'accounts/dashboard/admin/admin_edit.html', context)


@method_decorator(login_required, name='dispatch')
class AdminInviteView(View):
    """
    Dedicated `/admins/invite/` page — the 2-step invitation flow.

    GET  → render step 1 (email only).
    POST → handles both steps via the hidden ``invite_step`` field:
              invite_step=email   → validate email, render step 2
                                    with the email pre-filled.
              invite_step=details → validate full details, create
                                    the invitation, flash per-channel
                                    outcome, redirect back to step 1.
    """

    INVITE_TEMPLATE = 'accounts/dashboard/admin/invite_admin.html'

    def _base_context(self, request, *, invite_step='1',
                      invite_email='', step1_form=None, step2_form=None,
                      step1_errors=False, invite_success=None):
        if request.user.is_chief:
            pending = InvitationService.get_pending_invitations()
        else:
            pending = [
                inv for inv in InvitationService.get_pending_invitations()
                if inv.created_by_id == request.user.id
            ]

        can_invite = PermissionService.has_permission(request.user, 'can_invite_admins')
        available_permissions = PermissionService.get_available_permissions() if can_invite else []

        return {
            'invite_step': invite_step,
            'invite_email': invite_email,
            'invite_step1_form': step1_form or (InviteAdminForm() if can_invite else None),
            'invite_step2_form': step2_form or (
                InvitationDetailsAdminForm(initial={'email': invite_email}) if can_invite else None
            ),
            'invite_step1_errors': step1_errors,
            'invite_available_permissions': available_permissions,
            'pending_invitations': pending,
            'invite_success': invite_success,
            'page_title': 'Invite Admin - Caldan Construction and Consultancy Firm',
        }

    def get(self, request):
        if not request.user.is_admin:
            messages.error(request, 'Access denied. Admin privileges required.')
            return redirect('dashboard:overview')

        if not PermissionService.has_permission(request.user, 'can_invite_admins'):
            messages.error(request, 'You do not have permission to invite admins.')
            return redirect('accounts:admin_list')

        # Pull the rich success payload from the previous POST (if any)
        # and clear it so a refresh doesn't re-show the modal.
        success_payload = request.session.pop('invite_success', None)

        return render(
            request,
            self.INVITE_TEMPLATE,
            self._base_context(request, invite_success=success_payload),
        )

    def post(self, request):
        if not request.user.is_admin:
            messages.error(request, 'Access denied. Admin privileges required.')
            return redirect('dashboard:overview')

        if not PermissionService.has_permission(request.user, 'can_invite_admins'):
            messages.error(request, 'You do not have permission to invite admins.')
            return redirect('accounts:admin_list')

        # ----------------------------------------------------------------
        # Dispatch: prefer the 'email' value when BOTH 'email' and
        # 'details' are present (legacy single-form templates submitted
        # both hidden invite_step fields at once). Without this guard
        # the wrong branch fires and the user sees a silent refresh.
        # ----------------------------------------------------------------
        step_values = [v.lower() for v in request.POST.getlist('invite_step') if v]
        if 'email' in step_values and 'details' not in step_values:
            invite_step = 'email'
        elif 'details' in step_values and 'email' not in step_values:
            invite_step = 'details'
        elif 'email' in step_values:
            invite_step = 'email'
        else:
            invite_step = (step_values[0] if step_values else 'email')

        # ----------------------------------------------------------------
        # Step 1 — email only
        # ----------------------------------------------------------------
        if invite_step == 'email':
            form = InviteAdminForm(request.POST)
            if form.is_valid():
                email = form.cleaned_data['email'].lower().strip()
                return render(request, self.INVITE_TEMPLATE, self._base_context(
                    request,
                    invite_step='2',
                    invite_email=email,
                    step2_form=InvitationDetailsAdminForm(initial={'email': email}),
                ))
            # Invalid email — bounce back to step 1 with errors.
            return render(request, self.INVITE_TEMPLATE, self._base_context(
                request,
                invite_step='1',
                step1_form=form,
                step1_errors=True,
            ))

        # ----------------------------------------------------------------
        # Step 2 — full details
        # ----------------------------------------------------------------
        if invite_step == 'details':
            prefill_email = (request.POST.get('email') or '').lower().strip()
            if not prefill_email:
                # Defensive: never silently redirect away from a
                # half-filled step 2 — show step 1 with a banner so
                # the chief understands what happened.
                messages.error(
                    request,
                    'We lost track of the recipient email. Please re-enter it.',
                )
                form = InviteAdminForm(initial={'email': ''})
                # Mark email field-level error so the banner renders.
                form.add_error(
                    'email',
                    'Please re-enter the recipient email to continue.',
                )
                return render(request, self.INVITE_TEMPLATE, self._base_context(
                    request,
                    invite_step='1',
                    step1_form=form,
                    step1_errors=True,
                ))

            form = InvitationDetailsAdminForm(request.POST)
            if form.is_valid():
                channels = form.cleaned_data['channels']
                permissions = {k: True for k in form.cleaned_data.get('permissions', [])}
                success, response = InvitationService.create_invitation(
                    email=prefill_email,
                    created_by=request.user,
                    request=request,
                    full_name=form.cleaned_data.get('full_name', ''),
                    phone=form.cleaned_data.get('phone', ''),
                    role=form.cleaned_data.get('role') or User.Role.PLATFORM_ADMIN,
                    permissions=permissions,
                    personal_message=form.cleaned_data.get('personal_message', ''),
                    send_email='email' in channels,
                    send_sms='sms' in channels,
                )
                if success:
                    # Surface a rich success modal on the next render with
                    # full context (recipient, channels, expiry) — the toast
                    # alone is too thin for a multi-channel send.
                    request.session['invite_success'] = {
                        'email': prefill_email,
                        'full_name': form.cleaned_data.get('full_name', '') or prefill_email,
                        'role': form.cleaned_data.get('role') or 'Platform Admin',
                        'channels_sent': list(response.get('channels', {}).keys()),
                        'expires_at': response.get('expires_at'),
                        'invitation_id': response.get('invitation_id'),
                    }
                    messages.success(
                        request,
                        response.get('message', f'Invitation sent to {prefill_email}.'),
                    )
                else:
                    messages.error(
                        request,
                        response.get('error', 'Failed to send invitation.'),
                    )
                return redirect('accounts:admin_invite')

            # Step 2 invalid — re-render with the email preserved.
            return render(request, self.INVITE_TEMPLATE, self._base_context(
                request,
                invite_step='2',
                invite_email=prefill_email,
                step2_form=form,
            ))

        messages.error(request, 'Unknown invitation step.')
        return redirect('accounts:admin_invite')


@method_decorator(login_required, name='dispatch')
class AdminInvitationResendView(View):
    """
    Re-deliver an existing pending invitation on a single channel
    (email or SMS). Chief-only.

    AJAX callers get a JSON response; non-AJAX callers get a redirect
    to the console with a Django message.
    """

    VALID_CHANNELS = {'email', 'sms'}

    def post(self, request, invitation_id, channel):
        # Only chief admins can resend invitations — they have the
        # platform-wide view and the responsibility.
        if not request.user.is_chief:
            return self._respond(
                request,
                ok=False,
                error='Only the Chief Admin can resend invitations.',
                status=403,
            )

        if channel not in self.VALID_CHANNELS:
            return self._respond(
                request,
                ok=False,
                error=f'Unknown channel "{channel}".',
                status=400,
            )

        success, response = InvitationService.resend(
            invitation_id=invitation_id,
            channel=channel,
            request=request,
        )

        if success:
            messages.success(
                request,
                response.get('message', f'{channel.title()} re-sent.'),
            )
        else:
            messages.error(
                request,
                response.get('error', f'{channel.title()} resend failed.'),
            )

        return self._respond(
            request,
            ok=success,
            error=response.get('error'),
            payload=response,
        )

    def _respond(self, request, *, ok, error=None, payload=None, status=200):
        """Return JSON to AJAX callers, redirect everyone else."""
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            body = {'ok': ok, 'error': error}
            if payload is not None:
                body.update(payload)
            return JsonResponse(body, status=status)

        return redirect('accounts:admin_list')


@method_decorator(login_required, name='dispatch')
class AdminLockView(View):
    """
    Manually lock a platform admin's account (chief only).
    """

    def post(self, request, admin_id):
        # Only chief admins can lock
        if not request.user.is_chief:
            messages.error(request, 'Only the Chief Admin can lock admin accounts.')
            return redirect('accounts:admin_list')

        admin = get_object_or_404(
            User,
            id=admin_id,
            role__in=[User.Role.CHIEF_ADMIN, User.Role.PLATFORM_ADMIN]
        )

        # Prevent self-lock
        if admin.id == request.user.id:
            messages.error(request, 'You cannot lock your own account.')
            return redirect('accounts:admin_list')

        # Prevent locking chief admins
        if admin.is_chief:
            messages.error(request, 'Cannot lock a Chief Admin account.')
            return redirect('accounts:admin_list')

        # Determine lock duration (default 24 h, configurable via POST)
        try:
            hours = int(request.POST.get('hours', 24))
        except (TypeError, ValueError):
            hours = 24
        hours = max(1, min(hours, 24 * 30))  # 1 hour to 30 days

        admin.locked_until = timezone.now() + timedelta(hours=hours)
        admin.failed_login_attempts = 0  # reset counter
        admin.save(update_fields=['locked_until', 'failed_login_attempts'])

        # Audit log
        AuditService.log_action(
            user=request.user,
            action=AuditLog.Action.ADMIN_LOCKED,
            entity_type='User',
            entity_id=admin.id,
            details={
                'admin_email': admin.email,
                'hours': hours,
                'until': admin.locked_until.isoformat(),
            },
            request=request
        )

        messages.success(
            request,
            f'{admin.full_name} has been locked for {hours} hours.'
        )
        logger.info(f"Admin {admin.email} locked by {request.user.email} for {hours}h")
        return redirect('accounts:admin_list')


@method_decorator(login_required, name='dispatch')
class AdminUnlockView(View):
    """
    Unlock a platform admin's account (chief only).
    """

    def post(self, request, admin_id):
        # Only chief admins can unlock
        if not request.user.is_chief:
            messages.error(request, 'Only the Chief Admin can unlock admin accounts.')
            return redirect('accounts:admin_list')

        admin = get_object_or_404(
            User,
            id=admin_id,
            role__in=[User.Role.CHIEF_ADMIN, User.Role.PLATFORM_ADMIN]
        )

        # Clear lock
        admin.locked_until = None
        admin.failed_login_attempts = 0
        admin.save(update_fields=['locked_until', 'failed_login_attempts'])

        # Audit log
        AuditService.log_action(
            user=request.user,
            action=AuditLog.Action.ADMIN_UNLOCKED,
            entity_type='User',
            entity_id=admin.id,
            details={
                'admin_email': admin.email,
            },
            request=request
        )

        messages.success(request, f'{admin.full_name} has been unlocked.')
        logger.info(f"Admin {admin.email} unlocked by {request.user.email}")
        return redirect('accounts:admin_list')