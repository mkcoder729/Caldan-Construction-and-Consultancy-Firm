"""
Service Service - CRUD operations and category management.
Caldan Construction - "Building Kenya's Future, One Project at a Time."
"""

import logging

from django.db.models import Q, Count
from django.shortcuts import get_object_or_404
from django.utils.text import slugify

from accounts.services.audit_service import AuditService
from services.models import Service

logger = logging.getLogger('caldan.services')


class ServiceService:
    """
    Service for service management operations.
    All methods are class methods following the service-oriented architecture.
    """

    @classmethod
    def get_all_services(cls, filters=None, page=1, per_page=20):
        """
        Get all services with optional filters.
        """
        queryset = Service.objects.all()

        if filters:
            # Search filter
            search = filters.get('search')
            if search:
                queryset = queryset.filter(
                    Q(name__icontains=search) |
                    Q(description__icontains=search) |
                    Q(category__icontains=search)
                )

            # Category filter
            category = filters.get('category')
            if category:
                queryset = queryset.filter(category=category)

            # Active filter
            is_active = filters.get('is_active')
            if is_active is not None:
                queryset = queryset.filter(is_active=is_active)

        # Order by display_order, then name
        queryset = queryset.order_by('display_order', 'name')

        # Pagination
        start = (page - 1) * per_page
        end = start + per_page
        total = queryset.count()

        return {
            'services': queryset[start:end],
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': (total + per_page - 1) // per_page if total > 0 else 1,
        }

    @classmethod
    def get_service(cls, service_id):
        """
        Get a single service by ID.
        """
        return get_object_or_404(Service, id=service_id)

    @classmethod
    def get_service_by_slug(cls, slug):
        """
        Get a single service by slug.
        """
        return get_object_or_404(Service, slug=slug, is_active=True)

    @classmethod
    def create_service(cls, data, user):
        """
        Create a new service.
        """
        # Handle slug
        if not data.get('slug'):
            data['slug'] = slugify(data.get('name', ''))

        # Ensure slug is unique
        slug = data['slug']
        counter = 1
        while Service.objects.filter(slug=slug).exists():
            slug = f"{data['slug']}-{counter}"
            counter += 1
        data['slug'] = slug

        # Handle features (JSON)
        if 'features' in data and isinstance(data['features'], list):
            data['features'] = data['features']

        # Check if display_order is already taken
        display_order = data.get('display_order', 0)
        if Service.objects.filter(display_order=display_order).exists():
            Service.objects.filter(display_order__gte=display_order).update(
                display_order=models.F('display_order') + 1
            )

        service = Service.objects.create(**data)

        # Log audit
        AuditService.log_action(
            user=user,
            action='SERVICE_CREATED',
            entity_type='Service',
            entity_id=str(service.id),
            details={
                'name': service.name,
                'category': service.category,
                'is_active': service.is_active,
            }
        )

        logger.info(f"Service created: {service.name} by {user.email}")
        return service

    @classmethod
    def update_service(cls, service_id, data, user):
        """
        Update an existing service.
        """
        service = cls.get_service(service_id)

        # Handle slug
        if data.get('slug'):
            slug = data['slug']
            # Ensure slug is unique (excluding this service)
            counter = 1
            while Service.objects.filter(slug=slug).exclude(id=service_id).exists():
                slug = f"{data['slug']}-{counter}"
                counter += 1
            data['slug'] = slug
        elif data.get('name'):
            slug = slugify(data['name'])
            counter = 1
            while Service.objects.filter(slug=slug).exclude(id=service_id).exists():
                slug = f"{slugify(data['name'])}-{counter}"
                counter += 1
            data['slug'] = slug

        # Handle features (JSON)
        if 'features' in data and isinstance(data['features'], list):
            data['features'] = data['features']

        # Handle display_order changes
        old_order = service.display_order
        new_order = data.get('display_order', old_order)

        if new_order != old_order:
            if new_order > old_order:
                # Moving down: shift others up
                Service.objects.filter(
                    display_order__gt=old_order,
                    display_order__lte=new_order
                ).exclude(id=service_id).update(
                    display_order=models.F('display_order') - 1
                )
            else:
                # Moving up: shift others down
                Service.objects.filter(
                    display_order__gte=new_order,
                    display_order__lt=old_order
                ).exclude(id=service_id).update(
                    display_order=models.F('display_order') + 1
                )

        # Update fields
        for key, value in data.items():
            setattr(service, key, value)
        service.save()

        # Log audit
        AuditService.log_action(
            user=user,
            action='SERVICE_UPDATED',
            entity_type='Service',
            entity_id=str(service.id),
            details={
                'name': service.name,
                'category': service.category,
                'is_active': service.is_active,
            }
        )

        logger.info(f"Service updated: {service.name} by {user.email}")
        return service

    @classmethod
    def delete_service(cls, service_id, user):
        """
        Delete a service.
        """
        service = cls.get_service(service_id)
        service_name = service.name

        # Log audit before deletion
        AuditService.log_action(
            user=user,
            action='SERVICE_DELETED',
            entity_type='Service',
            entity_id=str(service.id),
            details={
                'name': service.name,
                'category': service.category,
            }
        )

        service.delete()

        # Reorder remaining services
        cls._reorder_services()

        logger.info(f"Service deleted: {service_name} by {user.email}")
        return True

    @classmethod
    def _reorder_services(cls):
        """
        Reorder all services sequentially after deletion.
        """
        services = Service.objects.order_by('display_order', 'name')
        for idx, service in enumerate(services):
            if service.display_order != idx:
                service.display_order = idx
                service.save(update_fields=['display_order'])

    @classmethod
    def get_categories(cls):
        """
        Get all service categories with counts.
        """
        categories = []
        for category_code, category_label in Service.Category.choices:
            count = Service.objects.filter(category=category_code, is_active=True).count()
            categories.append({
                'code': category_code,
                'label': category_label,
                'count': count,
                'services': Service.objects.filter(category=category_code, is_active=True)
                          .order_by('display_order', 'name')[:10],
            })
        return categories

    @classmethod
    def get_stats(cls):
        """
        Get service statistics for dashboard.
        """
        total = Service.objects.count()
        active = Service.objects.filter(is_active=True).count()
        inactive = Service.objects.filter(is_active=False).count()

        # Category breakdown
        category_counts = {}
        for category_code, category_label in Service.Category.choices:
            count = Service.objects.filter(category=category_code, is_active=True).count()
            if count > 0:
                category_counts[category_label] = count

        return {
            'total': total,
            'active': active,
            'inactive': inactive,
            'category_counts': category_counts,
        }

    @classmethod
    def get_active_services(cls, limit=None):
        """
        Get all active services for public display.
        """
        queryset = Service.objects.filter(is_active=True)
        queryset = queryset.order_by('display_order', 'name')

        if limit:
            queryset = queryset[:limit]

        return queryset