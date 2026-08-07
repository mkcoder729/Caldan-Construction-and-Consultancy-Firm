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
#
# NOTE: seed_clients, seed_materials, seed_payments are intentionally
# OMITTED from the deploy seed. These modules have transactional/PII
# data and are managed through the dashboard, not populated from
# fixtures on every deploy. seed_products and seed_general_store are
# seeded because the shop needs them to function on a fresh deploy.
SEED_COMMANDS = [
    "seed_team",              # staff/test users
    "seed_services",          # service catalog
    "seed_projects",          # projects (may reference clients)
    "seed_blog",              # blog posts
    "seed_testimonials",      # testimonials (may reference clients)
    "seed_products",          # construction shop catalogue
    "seed_general_store",     # general-store catalogue (stationery, snacks, …)
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
                succeeded.append(name)
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
            # Re-raise the first failure so callers (e.g. entrypoint.sh)
            # can detect and exit non-zero when --stop-on-error is set.
            if stop_on_error:
                raise failed[0][1]
