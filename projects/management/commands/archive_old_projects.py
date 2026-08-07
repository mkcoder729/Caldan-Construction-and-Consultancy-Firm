# Archive Old Projects Command - Caldan Construction
# "Building Kenya's Future, One Project at a Time."

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from projects.tasks import archive_old_completed_projects
from projects.models import Project


class Command(BaseCommand):
    """
    Manually trigger archiving of old completed projects.

    Usage:
        python manage.py archive_old_projects
        python manage.py archive_old_projects --days=60
        python manage.py archive_old_projects --dry-run
        python manage.py archive_old_projects --project=PRJ-2026-0001
    """

    help = 'Archive old completed projects'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=90,
            help='Archive projects completed more than N days ago (default: 90)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be archived without actually archiving'
        )
        parser.add_argument(
            '--project',
            type=str,
            help='Archive a specific project by project_code'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🚀 Starting archive old projects task...'))
        self.stdout.write(f'📅 Current time: {timezone.now().strftime("%Y-%m-%d %H:%M:%S EAT")}')

        days = options.get('days', 90)
        dry_run = options.get('dry_run', False)
        specific_project = options.get('project')

        cutoff_date = timezone.now().date() - timedelta(days=days)

        # Get projects to archive
        if specific_project:
            projects = Project.objects.filter(
                project_code=specific_project,
                status='COMPLETED',
                is_archived=False
            )
            if not projects.exists():
                self.stdout.write(
                    self.style.WARNING(
                        f'⚠️ Project {specific_project} not found or not eligible for archiving.'
                    )
                )
                return
        else:
            projects = Project.objects.filter(
                status='COMPLETED',
                is_archived=False,
                updated_at__date__lt=cutoff_date
            )

        count = projects.count()

        if count == 0:
            self.stdout.write(self.style.WARNING('⚠️ No projects to archive.'))
            return

        self.stdout.write(f'📋 Found {count} project(s) to archive.')

        if dry_run:
            self.stdout.write(self.style.WARNING('🔄 DRY RUN - No changes will be made.'))
            for project in projects:
                self.stdout.write(f'  - {project.project_code}: {project.name} (completed {project.end_date})')
            self.stdout.write(f'\n✅ Dry run complete. Would archive {count} project(s).')
            return

        # Confirm if more than 10 projects
        if count > 10:
            confirm = input(f'⚠️ This will archive {count} projects. Continue? (y/N): ')
            if confirm.lower() != 'y':
                self.stdout.write(self.style.WARNING('❌ Operation cancelled.'))
                return

        # Execute archive
        self.stdout.write('📋 Archiving projects...')
        result = archive_old_completed_projects.delay().get(timeout=300)

        self.stdout.write(
            self.style.SUCCESS(
                f'✅ Archived {result.get("archived", 0)} project(s).'
            )
        )

        if result.get('archived', 0) < count:
            self.stdout.write(
                self.style.WARNING(
                    f'⚠️ Some projects could not be archived. Check logs for details.'
                )
            )

        self.stdout.write(self.style.SUCCESS('✅ Archive task complete!'))