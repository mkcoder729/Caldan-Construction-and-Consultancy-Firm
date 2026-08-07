"""
Invitation Views - Accept admin invitations.

This module handles the acceptance of admin invitations with
secure token validation and account creation.
"""

import logging
from django.shortcuts import render, redirect
from django.contrib import messages
from django.views import View
from django.utils import timezone

from accounts.models import AdminInvitation
from accounts.forms.invitation_form import AcceptInvitationForm
from accounts.services.invitation_service import InvitationService
from accounts.services.audit_service import AuditService

logger = logging.getLogger('caldan')


class AcceptInvitationView(View):
    """
    Accept admin invitation view.
    """

    def dispatch(self, request, *args, **kwargs):
        """
        Redirect if already logged in.
        """
        if request.user.is_authenticated:
            messages.warning(request, 'You are already logged in.')
            return redirect('dashboard:overview')
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, token):
        """
        Display invitation acceptance form.
        """
        # Validate token
        invitation_status = InvitationService.get_invitation_status(token)

        if not invitation_status.get('valid', False):
            messages.error(request, invitation_status.get('error', 'Invalid invitation link.'))
            return redirect('accounts:login')

        # Pre-fill the form with everything the chief already collected
        # when sending the invitation. The invitee only has to pick a
        # password — name/phone/role are not a surprise.
        prefill = {'email': invitation_status.get('email')}
        if invitation_status.get('full_name'):
            prefill['full_name'] = invitation_status['full_name']
        if invitation_status.get('phone'):
            prefill['phone'] = invitation_status['phone']

        form = AcceptInvitationForm(initial=prefill)

        context = {
            'form': form,
            'token': token,
            'invitation': invitation_status,
            'hide_navbar': True,
            'hide_footer': True,
            'page_title': 'Accept Invitation - Caldan Construction and Consultancy Firm',
        }
        return render(request, 'accounts/dashboard/admin/invite_accept.html', context)

    def post(self, request, token):
        """
        Process invitation acceptance.

        The user does NOT supply a password here — the system generates a
        temporary one when the invitation is created and emails it to
        the invitee. The invitee only confirms their name and phone, and
        is required to set a real password the moment they sign in.
        """
        form = AcceptInvitationForm(request.POST)

        if form.is_valid():
            full_name = form.cleaned_data['full_name']
            phone = form.cleaned_data['phone']

            # Accept invitation — the service uses the system-generated
            # temp password stored on the invitation row.
            success, response = InvitationService.accept_invitation(
                token=token,
                password=None,           # signal: use invitation.temp_password
                full_name=full_name,
                phone=phone,
                request=request
            )

            if success:
                messages.success(
                    request,
                    'Account created. Sign in with the temporary password from '
                    'your invitation email — you will be asked to set a new '
                    'password immediately.',
                )
                return redirect('accounts:login')
            else:
                messages.error(request, response.get('error', 'Failed to create account.'))
                return render(request, 'accounts/dashboard/admin/invite_accept.html', {
                    'form': form,
                    'token': token,
                    'hide_navbar': True,
                    'hide_footer': True,
                    'page_title': 'Accept Invitation - Caldan Construction and Consultancy Firm',
                })

        # Form is invalid
        return render(request, 'accounts/dashboard/admin/invite_accept.html', {
            'form': form,
            'token': token,
            'hide_navbar': True,
            'hide_footer': True,
            'page_title': 'Accept Invitation - Caldan Construction and Consultancy Firm',
        })


class InvitationStatusView(View):
    """
    Check invitation status view.
    """

    def get(self, request, token):
        """
        Display invitation status.
        """
        status = InvitationService.get_invitation_status(token)

        context = {
            'status': status,
            'token': token,
            'hide_navbar': True,
            'hide_footer': True,
            'page_title': 'Invitation Status - Caldan Construction and Consultancy Firm',
        }
        return render(request, 'accounts/dashboard/admin/invite_status.html', context)