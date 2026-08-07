"""
Client Service - CRUD operations and lead management.
Caldan Construction - "Building Kenya's Future, One Project at a Time."
"""

import logging
from datetime import timedelta

from django.db.models import Q, Count, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone

from accounts.services.audit_service import AuditService
from clients.models import Client

logger = logging.getLogger('caldan.clients')


class ClientService:
    """
    Service for client management operations.
    All methods are class methods following the service-oriented architecture.
    """

    @classmethod
    def get_all_clients(cls, filters=None, page=1, per_page=20):
        """
        Get all clients with optional filters.
        """
        queryset = Client.objects.all()

        if filters:
            # Search filter
            search = filters.get('search')
            if search:
                queryset = queryset.filter(
                    Q(name__icontains=search) |
                    Q(company_name__icontains=search) |
                    Q(email__icontains=search) |
                    Q(phone__icontains=search) |
                    Q(county__icontains=search)
                )

            # Status filter
            status = filters.get('status')
            if status:
                queryset = queryset.filter(status=status)

            # Type filter
            client_type = filters.get('type')
            if client_type:
                queryset = queryset.filter(type=client_type)

            # Source filter
            source = filters.get('source')
            if source:
                queryset = queryset.filter(source__icontains=source)

            # Date range filter
            date_from = filters.get('date_from')
            if date_from:
                queryset = queryset.filter(created_at__date__gte=date_from)

            date_to = filters.get('date_to')
            if date_to:
                queryset = queryset.filter(created_at__date__lte=date_to)

            # Exclude leads (for client list only)
            exclude_leads = filters.get('exclude_leads', False)
            if exclude_leads:
                queryset = queryset.exclude(status='LEAD')

        # Order by created_at
        queryset = queryset.order_by('-created_at')

        # Pagination
        start = (page - 1) * per_page
        end = start + per_page
        total = queryset.count()

        return {
            'clients': queryset[start:end],
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': (total + per_page - 1) // per_page if total > 0 else 1,
        }

    @classmethod
    def get_client(cls, client_id):
        """
        Get a single client by ID.
        """
        return get_object_or_404(Client, id=client_id)

    @classmethod
    def create_client(cls, data, user):
        """
        Create a new client.
        """
        client = Client.objects.create(**data)

        # Log audit
        AuditService.log_action(
            user=user,
            action='CLIENT_CREATED',
            entity_type='Client',
            entity_id=str(client.id),
            details={
                'name': client.name,
                'email': client.email,
                'phone': client.phone,
                'type': client.type,
                'status': client.status,
                'source': client.source,
            }
        )

        logger.info(f"Client created: {client.name or client.company_name} by {user.email}")
        return client

    @classmethod
    def update_client(cls, client_id, data, user):
        """
        Update an existing client.
        """
        client = cls.get_client(client_id)

        # Store old values for audit
        old_name = client.name
        old_status = client.status

        # Update fields
        for key, value in data.items():
            setattr(client, key, value)
        client.save()

        # Log audit
        AuditService.log_action(
            user=user,
            action='CLIENT_UPDATED',
            entity_type='Client',
            entity_id=str(client.id),
            details={
                'name': client.name,
                'old_name': old_name,
                'old_status': old_status,
                'new_status': client.status,
                'email': client.email,
                'phone': client.phone,
            }
        )

        logger.info(f"Client updated: {client.name or client.company_name} by {user.email}")
        return client

    @classmethod
    def delete_client(cls, client_id, user):
        """
        Delete a client.
        """
        client = cls.get_client(client_id)
        client_name = client.name or client.company_name or client.email

        # Log audit before deletion
        AuditService.log_action(
            user=user,
            action='CLIENT_DELETED',
            entity_type='Client',
            entity_id=str(client.id),
            details={
                'name': client_name,
                'email': client.email,
                'phone': client.phone,
            }
        )

        client.delete()

        logger.info(f"Client deleted: {client_name} by {user.email}")
        return True

    @classmethod
    def convert_to_active(cls, client_id, user):
        """
        Convert a lead to an active client.
        """
        client = cls.get_client(client_id)

        if client.status != 'LEAD':
            raise ValueError('Only leads can be converted to active clients.')

        old_status = client.status
        client.status = 'ACTIVE'
        client.save(update_fields=['status', 'updated_at'])

        # Log audit
        AuditService.log_action(
            user=user,
            action='CLIENT_CONVERTED',
            entity_type='Client',
            entity_id=str(client.id),
            details={
                'name': client.name or client.company_name,
                'old_status': old_status,
                'new_status': client.status,
            }
        )

        logger.info(f"Client converted from lead to active: {client.name or client.company_name} by {user.email}")
        return client

    @classmethod
    def get_leads(cls, filters=None, page=1, per_page=20):
        """
        Get all leads (clients with status LEAD).
        """
        queryset = Client.objects.filter(status='LEAD')

        if filters:
            search = filters.get('search')
            if search:
                queryset = queryset.filter(
                    Q(name__icontains=search) |
                    Q(company_name__icontains=search) |
                    Q(email__icontains=search) |
                    Q(phone__icontains=search)
                )

            # Source filter
            source = filters.get('source')
            if source:
                queryset = queryset.filter(source__icontains=source)

            # Date range filter
            date_from = filters.get('date_from')
            if date_from:
                queryset = queryset.filter(created_at__date__gte=date_from)

            date_to = filters.get('date_to')
            if date_to:
                queryset = queryset.filter(created_at__date__lte=date_to)

        queryset = queryset.order_by('-created_at')

        start = (page - 1) * per_page
        end = start + per_page
        total = queryset.count()

        return {
            'leads': queryset[start:end],
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': (total + per_page - 1) // per_page if total > 0 else 1,
        }

    @classmethod
    def get_stats(cls):
        """
        Get client statistics for dashboard.
        """
        total = Client.objects.count()
        leads = Client.objects.filter(status='LEAD').count()
        active = Client.objects.filter(status='ACTIVE').count()
        inactive = Client.objects.filter(status='INACTIVE').count()
        converted = Client.objects.filter(status='CONVERTED').count()

        # Type breakdown
        type_counts = {}
        for type_code, type_label in Client.Type.choices:
            count = Client.objects.filter(type=type_code).count()
            if count > 0:
                type_counts[type_label] = count

        # Source breakdown
        source_counts = {}
        sources = Client.objects.values('source').annotate(count=Count('id'))
        for source in sources:
            if source['source']:
                source_counts[source['source']] = source['count']

        # Recent activity (last 7 days)
        week_ago = timezone.now() - timedelta(days=7)
        new_this_week = Client.objects.filter(created_at__gte=week_ago).count()

        return {
            'total': total,
            'leads': leads,
            'active': active,
            'inactive': inactive,
            'converted': converted,
            'new_this_week': new_this_week,
            'type_counts': type_counts,
            'source_counts': source_counts,
        }

    @classmethod
    def create_from_contact_form(cls, data, user=None):
        """
        Create a client from a contact form submission.
        """
        client = Client.objects.create(
            name=data.get('name'),
            email=data.get('email'),
            phone=data.get('phone'),
            type='INDIVIDUAL',
            status='LEAD',
            source='Website Contact Form',
            notes=f"Contact Form Submission:\n{data.get('message', '')[:500]}",
        )

        if user:
            AuditService.log_action(
                user=user,
                action='CLIENT_CREATED_FROM_CONTACT',
                entity_type='Client',
                entity_id=str(client.id),
                details={
                    'name': client.name,
                    'email': client.email,
                    'phone': client.phone,
                    'source': client.source,
                }
            )

        logger.info(f"Client created from contact form: {client.name} - {client.email}")
        return client

    @classmethod
    def create_from_quote_request(cls, data, user=None):
        """
        Create a client from a quote request form.
        """
        client = Client.objects.create(
            name=data.get('name'),
            email=data.get('email'),
            phone=data.get('phone'),
            type='INDIVIDUAL',
            status='LEAD',
            source='Website Quote Request',
            notes=f"Quote Request:\n"
                  f"Project Type: {data.get('project_type', 'N/A')}\n"
                  f"Budget: {data.get('budget', 'N/A')}\n"
                  f"Timeline: {data.get('timeline', 'N/A')}\n\n"
                  f"Details:\n{data.get('details', '')[:500]}",
        )

        if user:
            AuditService.log_action(
                user=user,
                action='CLIENT_CREATED_FROM_QUOTE',
                entity_type='Client',
                entity_id=str(client.id),
                details={
                    'name': client.name,
                    'email': client.email,
                    'phone': client.phone,
                    'source': client.source,
                }
            )

        logger.info(f"Client created from quote request: {client.name} - {client.email}")
        return client