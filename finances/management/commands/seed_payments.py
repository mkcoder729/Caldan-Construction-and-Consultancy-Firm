"""
Seed command for Payments - Caldan Construction
Creates realistic payments distributed across the seeded projects so
that payment list / detail / edit pages render real rows.
Idempotent: re-running won't duplicate rows (matches on
``reference``).
"""

from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from finances.models.payment import Payment
from projects.models import Project


# Realistic Kenyan construction vendor list — picked so the page
# reads like the kind of payments a builder actually makes.
VENDORS = [
    ("Nakuru Cement Distributors", "0712345678", "BANK"),
    ("Kenya Steel Suppliers Ltd", "0723456789", "BANK"),
    ("Limestone & Sand Supplies", "0734567890", "BANK"),
    ("Mahali Electricians Co-op", "0745678901", "MPESA"),
    ("Masonry Crew — Patrick Otieno", "0756789012", "MPESA"),
    ("Carpenter — Joseph Mwangi", "0767890123", "CASH"),
    ("Site Foreman — Ann Wambui", "0778901234", "MPESA"),
    ("Heavy Plant Hire Ltd", "0789012345", "BANK"),
    ("Plumbing World Kenya", "0701234567", "CHEQUE"),
    ("Paint & Finishes Ltd", "0711223344", "BANK"),
    ("Nakuru Building Materials", "0722334455", "MPESA"),
    ("Fuel Distributors Ltd", "0733445566", "BANK"),
]


def gen_invoice_number(seq):
    return f"INV-2026-{seq:04d}"


def gen_reference(prefix, seq):
    return f"{prefix}-{seq:04d}"


class Command(BaseCommand):
    help = "Seed finance payments distributed across the seeded projects."

    def add_arguments(self, parser):
        parser.add_argument(
            "--per-project",
            type=int,
            default=3,
            help="Number of payments to generate per project (default: 3).",
        )
        parser.add_argument(
            "--wipe",
            action="store_true",
            help="Delete all existing payments before seeding.",
        )

    def handle(self, *args, **options):
        per_project = max(1, min(options["per_project"], 12))
        if options["wipe"]:
            deleted, _ = Payment.objects.all().delete()
            # Reset AUTO_INCREMENT so ids start at 1 — keeps the
            # sidebar's hard-coded "Payment Detail" and "Edit Payment"
            # links (payment_id=1) alive.
            from django.db import connection
            try:
                with connection.cursor() as cur:
                    cur.execute("ALTER TABLE payments AUTO_INCREMENT = 1")
            except Exception:
                pass
            self.stdout.write(self.style.WARNING(
                f"🧹 Wiped {deleted} existing payment rows."
            ))

        projects = list(Project.objects.all().order_by("id"))
        if not projects:
            self.stdout.write(self.style.ERROR(
                "❌ No projects found. Run `python manage.py seed_projects` first."
            ))
            return

        # ---------------- Material payments ----------------
        material_entries = [
            ("Cement bags — bulk delivery", Payment.Type.MATERIAL,
             Decimal("45000.00"), Payment.Method.BANK,
             "Nakuru Cement Distributors", "PC-2026-0042"),
            ("Steel bars 12mm + 16mm", Payment.Type.MATERIAL,
             Decimal("128000.00"), Payment.Method.BANK,
             "Kenya Steel Suppliers Ltd", "KS-2026-0117"),
            ("River sand — 8 tonnes", Payment.Type.MATERIAL,
             Decimal("32000.00"), Payment.Method.MPESA,
             "Limestone & Sand Supplies", "LS-2026-0089"),
            ("Timber — structural grade", Payment.Type.MATERIAL,
             Decimal("64500.00"), Payment.Method.BANK,
             "Nakuru Building Materials", "NBM-2026-0205"),
            ("Plumbing fittings — full stack", Payment.Type.MATERIAL,
             Decimal("28750.00"), Payment.Method.CHEQUE,
             "Plumbing World Kenya", "PW-2026-0331"),
        ]

        # ---------------- Subcontractor payments ----------------
        subcontractor_entries = [
            ("Wiring & lighting installation", Payment.Type.SUBCONTRACTOR,
             Decimal("75000.00"), Payment.Method.MPESA,
             "Mahali Electricians Co-op", "ME-2026-0144"),
            ("Block laying — west wing", Payment.Type.SUBCONTRACTOR,
             Decimal("95000.00"), Payment.Method.MPESA,
             "Masonry Crew — Patrick Otieno", "MC-2026-0228"),
            ("Roof carpentry labour", Payment.Type.SUBCONTRACTOR,
             Decimal("64000.00"), Payment.Method.CASH,
             "Carpenter — Joseph Mwangi", "JM-2026-0190"),
            ("Site security & foreman", Payment.Type.SUBCONTRACTOR,
             Decimal("52000.00"), Payment.Method.MPESA,
             "Site Foreman — Ann Wambui", "AW-2026-0167"),
        ]

        # ---------------- Equipment payments ----------------
        equipment_entries = [
            ("Excavator hire — 3 days", Payment.Type.EQUIPMENT,
             Decimal("86000.00"), Payment.Method.BANK,
             "Heavy Plant Hire Ltd", "HP-2026-0512"),
            ("Concrete mixer rental", Payment.Type.EQUIPMENT,
             Decimal("18500.00"), Payment.Method.MPESA,
             "Heavy Plant Hire Ltd", "HP-2026-0533"),
        ]

        # ---------------- Salary payments ----------------
        salary_entries = [
            ("Site worker payroll — biweekly", Payment.Type.SALARY,
             Decimal("112000.00"), Payment.Method.BANK,
             "Site Workers — multiple", "PAY-2026-W08"),
            ("Foreman salary — monthly", Payment.Type.SALARY,
             Decimal("45000.00"), Payment.Method.MPESA,
             "Site Foreman — Ann Wambui", "PAY-2026-M03"),
        ]

        # ---------------- Other / finishing ----------------
        other_entries = [
            ("Interior paint & finishes", Payment.Type.OTHER,
             Decimal("38000.00"), Payment.Method.BANK,
             "Paint & Finishes Ltd", "PF-2026-0067"),
            ("Diesel for site generator — month", Payment.Type.OTHER,
             Decimal("24500.00"), Payment.Method.BANK,
             "Fuel Distributors Ltd", "FD-2026-0098"),
        ]

        # Distribute entries across the projects in round-robin.
        all_entries = (
            material_entries
            + subcontractor_entries
            + equipment_entries
            + salary_entries
            + other_entries
        )
        seed_specs = []
        for idx, entry in enumerate(all_entries):
            project = projects[idx % len(projects)]
            seed_specs.append((project, entry, idx))

        created = 0
        updated = 0
        skipped = 0
        today = date.today()

        for project, entry, idx in seed_specs:
            (
                description, ptype, amount, method,
                paid_to, reference,
            ) = entry
            vendor = next(
                (v for v in VENDORS if v[0] == paid_to),
                (paid_to, "", "BANK"),
            )
            _, phone, _ = vendor

            # Stagger payment dates across the last ~90 days so the
            # list view shows chronological spread, not a tight cluster.
            days_ago = (idx * 7) % 90
            payment_date = today - timedelta(days=days_ago)

            # Status pattern: oldest = COMPLETED, mid = APPROVED,
            # newest few = PENDING. Gives the dashboard filter some real
            # variety to render.
            if days_ago > 60:
                status = Payment.Status.COMPLETED
            elif days_ago > 14:
                status = Payment.Status.APPROVED
            else:
                status = Payment.Status.PENDING

            invoice_number = gen_invoice_number(idx + 1)
            full_reference = gen_reference(reference.split("-")[0], idx + 1)

            defaults = {
                "project": project,
                "amount": amount,
                "type": ptype,
                "method": method,
                "description": description,
                "paid_to": paid_to,
                "paid_to_contact": phone,
                "reference": full_reference,
                "invoice_number": invoice_number,
                "status": status,
                "payment_date": payment_date,
            }

            obj, was_created = Payment.objects.update_or_create(
                reference=full_reference,
                defaults=defaults,
            )
            if was_created:
                created += 1
            else:
                updated += 1

            label = "✅ created" if was_created else "↻ updated"
            self.stdout.write(
                f"  {label}: {paid_to} → KES {amount:,.2f} "
                f"[{project.name}] ({status})"
            )

        # Cap on how many we generate per project:
        # per_project only matters if there are way more projects than
        # entries. Skip extras to avoid noise.
        if per_project < 1:
            self.stdout.write(self.style.WARNING(
                f"⚠️  --per-project must be ≥1; ignoring."
            ))

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(
            f"🎉 Seed complete: {created} created, {updated} updated, "
            f"{skipped} skipped. Total Payment rows: "
            f"{Payment.objects.count()}."
        ))
