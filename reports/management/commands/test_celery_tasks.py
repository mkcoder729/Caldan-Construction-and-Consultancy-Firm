"""
Test runner for the scheduled Celery tasks 16-21.

Runs each task synchronously (no broker / worker needed) so you can
verify the email + PDF attachment pipeline without standing up Celery.

Tasks covered (the user's "16 to 21"):

  16. notifications.send_weekly_audit          → bi-weekly audit report (PDF)
  17. inventory.send_daily_stock_summary        → daily stock summary  (PDF)
  18. projects.generate_weekly_project_report   → weekly project report (PDF)
  19. dashboard.generate_daily_summary          → daily dashboard summary (PDF)
  20. projects.send_overdue_milestone_reminders → overdue milestone alerts
  21. accounts.send_account_activation_reminder → per-user activation reminder

Usage:
    python manage.py test_celery_tasks              # run all
    python manage.py test_celery_tasks --task 17    # run a single one
    python manage.py test_celery_tasks --list       # show task numbers + names
"""

import io
import sys

# Force stdout to use utf-8 so emoji in log lines (⚠️, 📅, etc.)
# doesn't crash the Windows cp1252 console mid-run.
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
else:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from django.core.management.base import BaseCommand, CommandError

from notifications.tasks import send_weekly_audit, send_daily_reminders
from inventory.tasks import send_daily_stock_summary
from projects.tasks import (
    generate_weekly_project_report,
    send_overdue_milestone_reminders,
)
from dashboard.tasks import generate_daily_summary
from accounts.tasks import send_account_activation_reminder


TASKS = {
    16: ('notifications.send_weekly_audit',          'send_weekly_audit',                 send_weekly_audit),
    17: ('inventory.send_daily_stock_summary',       'send_daily_stock_summary',          send_daily_stock_summary),
    18: ('projects.generate_weekly_project_report',  'generate_weekly_project_report',    generate_weekly_project_report),
    19: ('dashboard.generate_daily_summary',         'generate_daily_summary',            generate_daily_summary),
    20: ('projects.send_overdue_milestone_reminders','send_overdue_milestone_reminders',  send_overdue_milestone_reminders),
    21: ('accounts.send_account_activation_reminder','send_account_activation_reminder',  send_account_activation_reminder),
}


class Command(BaseCommand):
    help = 'Run scheduled Celery tasks synchronously (no broker needed) for testing.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--task',
            type=int,
            choices=sorted(TASKS.keys()),
            help='Number of the task to run (16-21). Default: run all.',
        )
        parser.add_argument(
            '--user-id',
            type=int,
            default=None,
            help='For task 21 (account activation reminder): the user ID to remind.',
        )
        parser.add_argument(
            '--list',
            action='store_true',
            help='List every task with its number and description, then exit.',
        )

    def handle(self, *args, **options):
        if options['list']:
            self.stdout.write(self.style.SUCCESS('Scheduled tasks (16-21):'))
            for num in sorted(TASKS):
                name, _, _ = TASKS[num]
                self.stdout.write(f'  {num:>2}. {name}')
            return

        selected = options.get('task')
        user_id = options.get('user_id')
        numbers = [selected] if selected else sorted(TASKS.keys())

        self.stdout.write(self.style.NOTICE(f'Running task(s): {numbers}'))
        self.stdout.write('')

        for num in numbers:
            _, label, task = TASKS[num]

            self.stdout.write(self.style.SUCCESS(f'=== Task {num}: {label} ==='))
            try:
                # The Celery task decorator wraps the function in a
                # `.run()` proxy that executes the body synchronously
                # when invoked as a callable. `apply()` does the same
                # without touching the broker.
                if num == 21 and user_id is not None:
                    result = task.apply(args=(user_id,))
                else:
                    result = task.apply()
                # Celery EagerResult exposes .get() / .result as the return value.
                value = result.get() if hasattr(result, 'get') else result
                self.stdout.write(self.style.SUCCESS(f'  -> result: {value}'))
            except Exception as exc:
                self.stdout.write(self.style.ERROR(f'  -> FAILED: {exc}'))
                if not options.get('task'):
                    # continue on failure so the whole sweep can finish
                    continue
                raise CommandError(f'Task {num} ({label}) failed: {exc}')
            self.stdout.write('')

        self.stdout.write(self.style.SUCCESS('Done.'))