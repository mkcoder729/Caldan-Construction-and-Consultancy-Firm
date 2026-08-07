"""
Seed all Caldan modules with sample/demo data.

Runs every per-app seed command in dependency order so that, e.g.,
clients exist before projects reference them.

Usage:
    python manage.py seed_all
"""

from django.core.management import call_command
from django.core.management.base import BaseCommand


# Order matters: seed foundational reference data first, then
# anything that has foreign keys to those.
SEED_COMMANDS = [
    "seed_team",          # staff/test users
    "seed_services",      # service catalog
    "seed_clients",       # client/customer records
    "seed_materials",     # inventory materials (no FKs to projects)
    "seed_projects",      # projects (may reference clients)
    "seed_payments",      # payments (FK to projects)
    "seed_products",      # shop products
    "seed_blog",          # blog posts
    "seed_testimonials",  # testimonials (may reference clients)
]


class Command(BaseCommand):
    help = "Run all seed commands in dependency order."

    def add_arguments(self, parser):
        parser.add_argument(
            "--stop-on-error",
            action="store_true",
            help="Halt the run if a single seed command raises.",
        )

    def handle(self, *args, **options):
        stop_on_error = options["stop_on_error"]
        succeeded = []
        failed = []

        for name in SEED_COMMANDS:
            self.stdout.write(self.style.NOTICE(f"\n=== {name} ==="))
            try:
                call_command(name)
            except KeyboardInterrupt:
                raise
            except Exception as exc:
                failed.append((name, exc))
                self.stderr.write(
                    self.style.ERROR(f"{name} failed: {exc}")
                )
                if stop_on_error:
                    break

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(
            f"Done. Succeeded: {len(succeeded)} | Failed: {len(failed)}"
        ))
        if failed:
            self.stdout.write(self.style.WARNING(
                "Failed commands: " + ", ".join(n for n, _ in failed)
            ))
