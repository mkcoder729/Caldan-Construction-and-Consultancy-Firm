"""
Team Management Views for Dashboard
Full CRUD operations for team members.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q

from team.models import TeamMember
from accounts.services.audit_service import AuditService


@login_required
def team_list(request):
    """
    List all team members.
    """
    queryset = TeamMember.objects.all()

    # Filters
    role = request.GET.get('role')
    search = request.GET.get('search')

    if role:
        queryset = queryset.filter(role=role)
    if search:
        queryset = queryset.filter(
            Q(name__icontains=search) |
            Q(title__icontains=search) |
            Q(bio__icontains=search)
        )

    # Pagination
    paginator = Paginator(queryset.order_by('display_order', 'name'), 20)
    page = request.GET.get('page', 1)
    members = paginator.get_page(page)

    # Role counts
    role_counts = {}
    for role_choice in TeamMember.Role.choices:
        role_counts[role_choice[0]] = TeamMember.objects.filter(role=role_choice[0]).count()

    context = {
        'page_title': 'Team Members',
        'page_icon': 'fa-user-tie',
        'members': members,
        'role_counts': role_counts,
        'current_role': role,
        'search': search,
    }
    return render(request, 'team/dashboard/admin/team/list.html', context)


@login_required
def team_create(request):
    """
    Create a new team member.
    """
    if request.method == 'POST':
        name = request.POST.get('name')
        role = request.POST.get('role')
        title = request.POST.get('title', '')
        bio = request.POST.get('bio', '')
        email = request.POST.get('email', '')
        phone = request.POST.get('phone', '')
        display_order = request.POST.get('display_order', 0)
        is_featured = request.POST.get('is_featured') == 'on'
        linkedin = request.POST.get('linkedin', '')
        twitter = request.POST.get('twitter', '')

        member = TeamMember.objects.create(
            name=name,
            role=role,
            title=title,
            bio=bio,
            email=email,
            phone=phone,
            display_order=display_order,
            is_featured=is_featured,
            linkedin=linkedin,
            twitter=twitter,
        )

        AuditService.log_action(
            user=request.user,
            action='TEAM_MEMBER_CREATED',
            entity_type='team_member',
            entity_id=member.id,
            details={'name': member.name, 'role': member.role}
        )

        messages.success(request, f'Team member "{name}" created successfully.')
        return redirect('dashboard:team_detail', pk=member.id)

    context = {
        'page_title': 'Add Team Member',
        'page_icon': 'fa-user-plus',
    }
    return render(request, 'team/dashboard/admin/team/create.html', context)


@login_required
def team_detail(request, pk):
    """
    View team member details.
    """
    member = get_object_or_404(TeamMember, id=pk)

    context = {
        'page_title': member.name,
        'page_icon': 'fa-info-circle',
        'member': member,
    }
    return render(request, 'team/dashboard/admin/team/detail.html', context)


@login_required
def team_edit(request, pk):
    """
    Edit team member details.
    """
    member = get_object_or_404(TeamMember, id=pk)

    if request.method == 'POST':
        member.name = request.POST.get('name')
        member.role = request.POST.get('role')
        member.title = request.POST.get('title', '')
        member.bio = request.POST.get('bio', '')
        member.email = request.POST.get('email', '')
        member.phone = request.POST.get('phone', '')
        member.display_order = request.POST.get('display_order', 0)
        member.is_featured = request.POST.get('is_featured') == 'on'
        member.linkedin = request.POST.get('linkedin', '')
        member.twitter = request.POST.get('twitter', '')
        member.save()

        AuditService.log_action(
            user=request.user,
            action='TEAM_MEMBER_UPDATED',
            entity_type='team_member',
            entity_id=member.id,
            details={'name': member.name}
        )

        messages.success(request, f'Team member "{member.name}" updated.')
        return redirect('dashboard:team_detail', pk=member.id)

    context = {
        'page_title': f'Edit {member.name}',
        'page_icon': 'fa-edit',
        'member': member,
    }
    return render(request, 'team/dashboard/admin/team/edit.html', context)


@login_required
def team_delete(request, pk):
    """
    Delete a team member.
    """
    member = get_object_or_404(TeamMember, id=pk)

    if request.method == 'POST':
        member_name = member.name
        member.delete()

        AuditService.log_action(
            user=request.user,
            action='TEAM_MEMBER_DELETED',
            entity_type='team_member',
            entity_id=member.id,
            details={'name': member_name}
        )

        messages.success(request, f'Team member "{member_name}" deleted.')
        return redirect('dashboard:team_list')

    context = {
        'page_title': f'Delete {member.name}',
        'page_icon': 'fa-trash',
        'member': member,
    }
    return render(request, 'team/dashboard/admin/team/delete.html', context)