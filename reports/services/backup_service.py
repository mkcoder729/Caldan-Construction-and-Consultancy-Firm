"""
Backup Service - Project backup creation, restoration, and management.
Caldan Construction - "Building Kenya's Future, One Project at a Time."
"""

import json
import logging
import os
from datetime import datetime

from django.conf import settings
from django.core.files.base import ContentFile
from django.utils import timezone

from cloudinary.uploader import upload
from cloudinary.utils import cloudinary_url

from reports.models import BackupRecord
from accounts.services.audit_service import AuditService

logger = logging.getLogger('caldan.reports')

# Wire Cloudinary SDK from Django settings (called once at import time)
try:
    import cloudinary
    from django.conf import settings as _django_settings
    _cfg = getattr(_django_settings, 'CLOUDINARY_STORAGE', {}) or {}
    if _cfg and not cloudinary.config().cloud_name:
        cloudinary.config(
            cloud_name=_cfg.get('CLOUD_NAME') or _cfg.get('cloud_name'),
            api_key=_cfg.get('API_KEY') or _cfg.get('api_key'),
            api_secret=_cfg.get('API_SECRET') or _cfg.get('api_secret'),
            secure=_cfg.get('SECURE', True),
        )
except Exception as _cloud_init_err:
    logger.debug(f"Cloudinary SDK not configured: {_cloud_init_err}")


class BackupService:
    """
    Service for creating, restoring, and managing project backups.
    Backups are stored as JSON in Cloudinary.
    """

    @classmethod
    def create_backup(cls, project_id, user, includes=None, notes=''):
        """
        Create a complete backup of a project.
        Returns the BackupRecord instance.
        """
        from projects.models import Project

        project = Project.objects.get(id=project_id)

        if includes is None:
            includes = {
                'milestones': True,
                'payments': True,
                'expenses': True,
                'materials': True,
                'gallery': False,
            }

        # Build backup data
        backup_data = cls._build_backup_data(project, includes)

        # Convert to JSON
        json_data = json.dumps(backup_data, default=str, indent=2)
        file_size = len(json_data.encode('utf-8'))

        # Upload to Cloudinary
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        filename = f"backup_{project.project_code}_{timestamp}.json"

        try:
            # Try Cloudinary first; fall back to local storage if not configured
            backup_url = None
            try:
                from django.conf import settings as _s
                if getattr(_s, 'CLOUDINARY_STORAGE', {}).get('API_KEY') or _s.CLOUDINARY_STORAGE.get('api_key'):
                    result = upload(
                        json_data,
                        folder=f"backups/{project.project_code}",
                        public_id=filename.replace('.json', ''),
                        resource_type='raw',
                        type='upload',
                    )
                    backup_url = result.get('secure_url', '')
            except Exception as cloud_err:
                logger.warning(f"Cloudinary upload failed ({cloud_err}); falling back to local storage.")

            if not backup_url:
                # Local storage fallback — write JSON to MEDIA_ROOT/backups/...
                # backup_file is a CloudinaryField (CharField subclass), so we
                # store the local path / data URI as a string.
                from django.conf import settings as _s
                import os
                media_root = getattr(_s, 'MEDIA_ROOT', None) or os.path.join(os.getcwd(), 'media')
                rel_folder = f"backups/{project.project_code}"
                abs_folder = os.path.join(media_root, rel_folder)
                os.makedirs(abs_folder, exist_ok=True)
                abs_path = os.path.join(abs_folder, filename)
                with open(abs_path, 'w', encoding='utf-8') as fh:
                    fh.write(json_data)
                # Store a relative URL/path the template can serve
                relative_path = f"{rel_folder}/{filename}"

                backup_record = BackupRecord.objects.create(
                    project=project,
                    backup_file=relative_path,
                    file_size=file_size,
                    record_count=backup_data.get('record_count', 0),
                    includes=includes,
                    notes=notes,
                    version='1.0.0',
                    created_by=user,
                )
                AuditService.log_action(
                    user=user,
                    action='BACKUP_CREATED',
                    entity_type='Project',
                    entity_id=str(project.id),
                    details={
                        'project_name': project.name,
                        'project_code': project.project_code,
                        'backup_id': backup_record.id,
                        'record_count': backup_record.record_count,
                        'file_size': file_size,
                        'storage': 'local-fallback',
                    }
                )
                logger.info(f"Backup stored locally at {abs_path}")
                return backup_record

            # Create backup record
            backup_record = BackupRecord.objects.create(
                project=project,
                backup_file=backup_url,
                file_size=file_size,
                record_count=backup_data.get('record_count', 0),
                includes=includes,
                notes=notes,
                version='1.0.0',
                created_by=user,
            )

            # Log audit
            AuditService.log_action(
                user=user,
                action='BACKUP_CREATED',
                entity_type='Project',
                entity_id=str(project.id),
                details={
                    'project_name': project.name,
                    'project_code': project.project_code,
                    'backup_id': backup_record.id,
                    'record_count': backup_record.record_count,
                    'file_size': file_size,
                }
            )

            logger.info(f"Backup created for {project.project_code} by {user.email}")
            return backup_record

        except Exception as e:
            logger.error(f"Failed to create backup for {project.project_code}: {str(e)}")
            raise

    @classmethod
    def _build_backup_data(cls, project, includes):
        """
        Build the backup data structure for a project.
        """
        backup_data = {
            'version': '1.0.0',
            'created_at': timezone.now().isoformat(),
            'project': {
                'id': project.id,
                'name': project.name,
                'project_code': project.project_code,
                'description': project.description,
                'location': project.location,
                'county': project.county,
                'town': project.town,
                'estate': project.estate,
                'latitude': float(project.latitude) if project.latitude else None,
                'longitude': float(project.longitude) if project.longitude else None,
                'start_date': project.start_date.isoformat() if project.start_date else None,
                'end_date': project.end_date.isoformat() if project.end_date else None,
                'estimated_completion': project.estimated_completion.isoformat() if project.estimated_completion else None,
                'actual_completion': project.actual_completion.isoformat() if project.actual_completion else None,
                'budget': float(project.budget),
                'spent': float(project.spent),
                'progress': float(project.progress),
                'status': project.status,
                'created_at': project.created_at.isoformat(),
                'updated_at': project.updated_at.isoformat(),
            },
            'milestones': [],
            'payments': [],
            'expenses': [],
            'materials': [],
            'gallery': [],
        }

        record_count = 1  # Count the project itself

        # Add milestones
        if includes.get('milestones', False):
            for milestone in project.milestones.all():
                backup_data['milestones'].append({
                    'id': milestone.id,
                    'title': milestone.title,
                    'description': milestone.description,
                    'target_date': milestone.target_date.isoformat() if milestone.target_date else None,
                    'completed_date': milestone.completed_date.isoformat() if milestone.completed_date else None,
                    'completion_percentage': float(milestone.completion_percentage),
                    'status': milestone.status,
                    'order': milestone.order,
                    'created_at': milestone.created_at.isoformat(),
                })
                record_count += 1

        # Add payments
        if includes.get('payments', False):
            for payment in project.payments.all():
                backup_data['payments'].append({
                    'id': payment.id,
                    'amount': float(payment.amount),
                    'type': payment.type,
                    'method': payment.method,
                    'description': payment.description,
                    'paid_to': payment.paid_to,
                    'paid_to_contact': payment.paid_to_contact,
                    'reference': payment.reference,
                    'invoice_number': payment.invoice_number,
                    'status': payment.status,
                    'payment_date': payment.payment_date.isoformat() if payment.payment_date else None,
                    'created_at': payment.created_at.isoformat(),
                })
                record_count += 1

        # Add expenses
        if includes.get('expenses', False):
            for expense in project.expenses.all():
                backup_data['expenses'].append({
                    'id': expense.id,
                    'amount': float(expense.amount),
                    'category': expense.category,
                    'description': expense.description,
                    'expense_date': expense.expense_date.isoformat() if expense.expense_date else None,
                    'vendor_name': expense.vendor_name,
                    'vendor_contact': expense.vendor_contact,
                    'receipt_number': expense.receipt_number,
                    'notes': expense.notes,
                    'created_at': expense.created_at.isoformat(),
                })
                record_count += 1

        # Add materials (inventory is global, not per-project)
        if includes.get('materials', False):
            from inventory.models import Material
            for material in Material.objects.all():
                backup_data['materials'].append({
                    'id': material.id,
                    'name': material.name,
                    'category': material.category,
                    'unit': material.unit,
                    'description': material.description,
                    'current_quantity': float(material.current_quantity),
                    'minimum_threshold': float(material.minimum_threshold),
                    'reorder_quantity': float(material.reorder_quantity),
                    'unit_cost': float(material.unit_cost),
                    'total_cost': float(material.total_cost),
                    'sku': material.sku,
                    'created_at': material.created_at.isoformat(),
                })
                record_count += 1

        backup_data['record_count'] = record_count
        return backup_data

    @classmethod
    def restore_backup(cls, backup_id, user):
        """
        Restore a project from backup.
        """
        from projects.models import Project

        backup_record = BackupRecord.objects.get(id=backup_id)

        if backup_record.is_deleted:
            raise ValueError("Cannot restore a deleted backup")

        # Fetch the backup data from Cloudinary
        try:
            import requests
            response = requests.get(backup_record.backup_file)
            response.raise_for_status()
            backup_data = response.json()
        except Exception as e:
            logger.error(f"Failed to fetch backup {backup_id}: {str(e)}")
            raise ValueError(f"Could not retrieve backup file: {str(e)}")

        # Check if project already exists
        project_code = backup_data['project']['project_code']
        existing_project = Project.objects.filter(project_code=project_code).first()

        if existing_project:
            raise ValueError(f"Project {project_code} already exists. Please delete or rename it first.")

        # Create project from backup
        project_data = backup_data['project']
        project = Project.objects.create(
            name=project_data['name'],
            project_code=project_data['project_code'],
            description=project_data.get('description', ''),
            location=project_data.get('location', ''),
            county=project_data.get('county', ''),
            town=project_data.get('town', ''),
            estate=project_data.get('estate', ''),
            start_date=datetime.fromisoformat(project_data['start_date']) if project_data.get('start_date') else None,
            end_date=datetime.fromisoformat(project_data['end_date']) if project_data.get('end_date') else None,
            estimated_completion=datetime.fromisoformat(project_data['estimated_completion']) if project_data.get('estimated_completion') else None,
            actual_completion=datetime.fromisoformat(project_data['actual_completion']) if project_data.get('actual_completion') else None,
            budget=project_data.get('budget', 0),
            spent=project_data.get('spent', 0),
            progress=project_data.get('progress', 0),
            status=project_data.get('status', 'PLANNING'),
        )

        # Restore milestones
        for milestone_data in backup_data.get('milestones', []):
            project.milestones.create(
                title=milestone_data['title'],
                description=milestone_data.get('description', ''),
                target_date=datetime.fromisoformat(milestone_data['target_date']) if milestone_data.get('target_date') else None,
                completed_date=datetime.fromisoformat(milestone_data['completed_date']) if milestone_data.get('completed_date') else None,
                completion_percentage=milestone_data.get('completion_percentage', 0),
                status=milestone_data.get('status', 'PENDING'),
                order=milestone_data.get('order', 0),
            )

        # Restore payments
        for payment_data in backup_data.get('payments', []):
            project.payments.create(
                amount=payment_data['amount'],
                type=payment_data.get('type', 'OTHER'),
                method=payment_data.get('method', 'CASH'),
                description=payment_data.get('description', ''),
                paid_to=payment_data.get('paid_to', ''),
                paid_to_contact=payment_data.get('paid_to_contact', ''),
                reference=payment_data.get('reference', ''),
                invoice_number=payment_data.get('invoice_number', ''),
                status=payment_data.get('status', 'COMPLETED'),
                payment_date=datetime.fromisoformat(payment_data['payment_date']) if payment_data.get('payment_date') else None,
            )

        # Restore expenses
        for expense_data in backup_data.get('expenses', []):
            project.expenses.create(
                amount=expense_data['amount'],
                category=expense_data.get('category', 'OTHER'),
                description=expense_data.get('description', ''),
                expense_date=datetime.fromisoformat(expense_data['expense_date']) if expense_data.get('expense_date') else None,
                vendor_name=expense_data.get('vendor_name', ''),
                vendor_contact=expense_data.get('vendor_contact', ''),
                receipt_number=expense_data.get('receipt_number', ''),
                notes=expense_data.get('notes', ''),
            )

        # Restore materials
        for material_data in backup_data.get('materials', []):
            project.materials.create(
                name=material_data['name'],
                category=material_data.get('category', 'OTHER'),
                unit=material_data.get('unit', 'OTHER'),
                description=material_data.get('description', ''),
                current_quantity=material_data.get('current_quantity', 0),
                minimum_threshold=material_data.get('minimum_threshold', 0),
                reorder_quantity=material_data.get('reorder_quantity', 0),
                unit_cost=material_data.get('unit_cost', 0),
                total_cost=material_data.get('total_cost', 0),
                sku=material_data.get('sku', ''),
            )

        # Mark backup as restored
        backup_record.mark_restored(user)

        # Log audit
        AuditService.log_action(
            user=user,
            action='BACKUP_RESTORED',
            entity_type='Project',
            entity_id=str(project.id),
            details={
                'project_name': project.name,
                'project_code': project.project_code,
                'backup_id': backup_record.id,
            }
        )

        logger.info(f"Backup {backup_id} restored as {project.project_code}")
        return project

    @classmethod
    def list_backups(cls, project_id=None):
        """
        List all backups, optionally filtered by project.
        """
        queryset = BackupRecord.objects.filter(is_deleted=False)

        if project_id:
            queryset = queryset.filter(project_id=project_id)

        return queryset.order_by('-created_at')

    @classmethod
    def delete_backup(cls, backup_id, user):
        """
        Delete a backup (soft delete).
        """
        backup_record = BackupRecord.objects.get(id=backup_id)
        backup_record.soft_delete(user)

        AuditService.log_action(
            user=user,
            action='BACKUP_DELETED',
            entity_type='BackupRecord',
            entity_id=str(backup_record.id),
            details={
                'project_name': backup_record.project.name,
                'project_code': backup_record.project.project_code,
            }
        )

        logger.info(f"Backup {backup_id} deleted by {user.email}")
        return backup_record

    @classmethod
    def get_backup_size(cls, backup_id):
        """
        Get the size of a backup file.
        """
        backup_record = BackupRecord.objects.get(id=backup_id)
        return backup_record.file_size