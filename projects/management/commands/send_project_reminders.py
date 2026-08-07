# Send Project Reminders Command - Caldan Construction
# "Building Kenya's Future, One Project at a Time."

from django.core.management.base import BaseCommand
from django.utils import timezone
from projects.tasks import send_overdue_milestone_reminders, send_upcoming_milestone_reminders


class Command(BaseCommand):
    """
    Manually trigger project reminder notifications.

    Usage:
        python manage.py send_project_reminders
        python manage.py send_project_reminders --days=14
        python manage.py send_project_reminders --overdue-only
    """

    help = 'Send project reminder notifications for milestones'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Number of days ahead to check for upcoming milestones (default: 7)'
        )
        parser.add_argument(
            '--overdue-only',
            action='store_true',
            help='Only send overdue milestone reminders'
        )
        parser.add_argument(
            '--upcoming-only',
            action='store_true',
            help='Only send upcoming milestone reminders'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🚀 Starting project reminder task...'))
        self.stdout.write(f'📅 Current time: {timezone.now().strftime("%Y-%m-%d %H:%M:%S EAT")}')

        results = {}

        # Send overdue reminders (unless upcoming-only flag is set)
        if not options.get('upcoming_only'):
            self.stdout.write('📋 Sending overdue milestone reminders...')
            result = send_overdue_milestone_reminders.delay().get(timeout=60)
            results['overdue'] = result
            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ Overdue reminders sent: {result.get("sent", 0)}/{result.get("total", 0)}'
                )
            )

        # Send upcoming reminders (unless overdue-only flag is set)
        if not options.get('overdue_only'):
            days = options.get('days', 7)
            self.stdout.write(f'📋 Sending upcoming milestone reminders ({days} days ahead)...')
            result = send_upcoming_milestone_reminders.delay(days).get(timeout=60)
            results['upcoming'] = result
            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ Upcoming reminders sent: {result.get("sent", 0)}/{result.get("total", 0)}'
                )
            )

        # Summary
        self.stdout.write(self.style.SUCCESS('\n📊 SUMMARY'))
        total_sent = results.get('overdue', {}).get('sent', 0) + results.get('upcoming', {}).get('sent', 0)
        total_found = results.get('overdue', {}).get('total', 0) + results.get('upcoming', {}).get('total', 0)
        self.stdout.write(f'Total reminders sent: {total_sent}/{total_found}')

        if total_sent == 0 and total_found == 0:
            self.stdout.write(self.style.WARNING('⚠️ No reminders to send. All milestones are on track!'))

        self.stdout.write(self.style.SUCCESS('✅ Project reminder task complete!'))