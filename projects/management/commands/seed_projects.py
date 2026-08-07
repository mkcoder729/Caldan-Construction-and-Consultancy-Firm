"""
Seed command for Projects - Caldan Construction
Creates projects from the company profile with Unsplash images.

Also seeds milestones for each project so the dashboard overview's
Project Milestones widget renders realistic data on a fresh database.
"""

import random
from datetime import date, datetime, timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.dateparse import parse_date

from projects.models import Project
from projects.models.milestone import Milestone
from services.models import Service


# Standard construction milestone template. The seed picks a sensible
# subset and completion % per project based on its current status.
STANDARD_MILESTONES = [
    "Site Survey & Mobilization",
    "Foundation Excavation & Casting",
    "Structural Framing",
    "Wall Construction",
    "Roofing & Waterproofing",
    "Plumbing & Electrical Rough-in",
    "Finishes (Plastering, Painting, Flooring)",
    "Final Fittings & Inspection",
    "Handover & Commissioning",
]


class Command(BaseCommand):
    help = "Seed projects data into the database with images and milestones"

    def handle(self, *args, **options):
        self.stdout.write("🌱 Seeding projects with images and milestones...")

        # Get service references
        try:
            design_service = Service.objects.get(slug="design-construction")
            renovations_service = Service.objects.get(slug="renovations")
            interior_service = Service.objects.get(slug="interior-design")
            welding_service = Service.objects.get(slug="welding-fabrication")
            concrete_service = Service.objects.get(slug="concrete-products")
            industrial_service = Service.objects.get(slug="industrial-floor-solutions")
            waterproofing_service = Service.objects.get(slug="waterproofing-works")
            infrastructure_service = Service.objects.get(slug="roads-stormwater-infrastructure")
        except Service.DoesNotExist:
            self.stdout.write(
                self.style.WARNING("⚠️ Services not found. Run seed_services first.")
            )
            return

        projects_data = [
            {
                "name": "Munanda Secondary School",
                "description": "Construction of a modern secondary school facility in Gilgil, Nakuru County. The project included 8 classrooms, administrative block, and a library.",
                "location": "Gilgil",
                "county": "Nakuru",
                "town": "Gilgil",
                "start_date": "2024-01-15",
                "end_date": "2024-08-20",
                "budget": 2000000.00,
                "status": Project.Status.COMPLETED,
                "image_url": "https://images.unsplash.com/photo-1580582932707-520aed937b7b?w=600&h=400&fit=crop&q=80",
                "services": [design_service, concrete_service],
            },
            {
                "name": "25 Units Apartment - Nakuru",
                "description": "Development of 25 modern residential apartment units in Nakuru town. Features include 2-bedroom and 3-bedroom units with parking.",
                "location": "Nakuru Town",
                "county": "Nakuru",
                "town": "Nakuru",
                "start_date": "2024-03-01",
                "budget": 35000000.00,
                "status": Project.Status.ACTIVE,
                "image_url": "https://images.unsplash.com/photo-1545324418-cc1a3fa10c00?w=600&h=400&fit=crop&q=80",
                "services": [
                    design_service,
                    renovations_service,
                    interior_service,
                ],
            },
            {
                "name": "18 Units Apartment - Dr. Nyangara",
                "description": "Construction of 18 high-end apartment units for Dr. Nyangara Naphtali. Modern finishes with premium amenities.",
                "location": "Nakuru",
                "county": "Nakuru",
                "town": "Nakuru",
                "start_date": "2024-02-01",
                "end_date": "2024-12-15",
                "budget": 22000000.00,
                "status": Project.Status.COMPLETED,
                "image_url": "https://images.unsplash.com/photo-1480074568708-e7b720bb3f09?w=600&h=400&fit=crop&q=80",
                "services": [
                    design_service,
                    renovations_service,
                    concrete_service,
                ],
            },
            {
                "name": "Oyarai Primary School",
                "description": "Construction of classrooms and administrative block at Oyarai Primary School. Project included 6 classrooms and staff offices.",
                "location": "Nakuru",
                "county": "Nakuru",
                "town": "Nakuru",
                "start_date": "2024-04-01",
                "end_date": "2024-07-30",
                "budget": 1100000.00,
                "status": Project.Status.COMPLETED,
                "image_url": "https://images.unsplash.com/photo-1580582932707-520aed937b7b?w=600&h=400&fit=crop&q=80",
                "services": [design_service, concrete_service],
            },
            {
                "name": "Oljorai Secondary School",
                "description": "Construction of a modern secondary school facility for the Ministry of Education. Includes 12 classrooms, science labs, and a hall.",
                "location": "Nakuru",
                "county": "Nakuru",
                "town": "Nakuru",
                "start_date": "2024-05-01",
                "end_date": "2024-11-30",
                "budget": 2100000.00,
                "status": Project.Status.ACTIVE,
                "image_url": "https://images.unsplash.com/photo-1580582932707-520aed937b7b?w=600&h=400&fit=crop&q=80",
                "services": [
                    design_service,
                    concrete_service,
                    infrastructure_service,
                ],
            },
            {
                "name": "Gilgil Secondary School - Koto Housing",
                "description": "Construction of dormitories and classrooms for Koto Housing at Gilgil Secondary School. Modern boarding facilities.",
                "location": "Gilgil",
                "county": "Nakuru",
                "town": "Gilgil",
                "start_date": "2024-06-01",
                "end_date": "2024-12-20",
                "budget": 6500000.00,
                "status": Project.Status.ACTIVE,
                "image_url": "https://images.unsplash.com/photo-1580582932707-520aed937b7b?w=600&h=400&fit=crop&q=80",
                "services": [
                    design_service,
                    renovations_service,
                    welding_service,
                ],
            },
            {
                "name": "Massonnaitte - James Mwangi",
                "description": "Construction of a modern massonnaitte residential building in Nakuru. Contemporary design with quality finishes.",
                "location": "Nakuru",
                "county": "Nakuru",
                "town": "Nakuru",
                "start_date": "2024-07-01",
                "end_date": "2025-01-15",
                "budget": 4200000.00,
                "status": Project.Status.ACTIVE,
                "image_url": "https://images.unsplash.com/photo-1512917774080-9991f1c4c750?w=600&h=400&fit=crop&q=80",
                "services": [
                    design_service,
                    renovations_service,
                    interior_service,
                    concrete_service,
                ],
            },
            {
                "name": "Nakuru CBD Commercial Building",
                "description": "Construction of a 5-storey commercial building in Nakuru CBD. Includes retail spaces and office floors.",
                "location": "Nakuru CBD",
                "county": "Nakuru",
                "town": "Nakuru",
                "start_date": "2025-01-10",
                "budget": 18000000.00,
                "status": Project.Status.ACTIVE,
                "image_url": "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?w=600&h=400&fit=crop&q=80",
                "services": [
                    design_service,
                    industrial_service,
                    waterproofing_service,
                    infrastructure_service,
                ],
            },
            {
                "name": "Nairobi Industrial Floor Project",
                "description": "Industrial epoxy flooring solution for a manufacturing facility in Nairobi. High-durability chemical-resistant flooring.",
                "location": "Nairobi",
                "county": "Nairobi",
                "town": "Nairobi",
                "start_date": "2025-02-01",
                "end_date": "2025-03-15",
                "budget": 3500000.00,
                "status": Project.Status.COMPLETED,
                "image_url": "https://images.unsplash.com/photo-1504384308090-c894fdcc538d?w=600&h=400&fit=crop&q=80",
                "services": [industrial_service],
            },
            {
                "name": "Nakuru Waterproofing Project",
                "description": "Complete waterproofing solution for a commercial building in Nakuru. Roof and basement waterproofing.",
                "location": "Nakuru",
                "county": "Nakuru",
                "town": "Nakuru",
                "start_date": "2025-03-01",
                "end_date": "2025-04-30",
                "budget": 1200000.00,
                "status": Project.Status.PLANNING,
                "image_url": "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?w=600&h=400&fit=crop&q=80",
                "services": [waterproofing_service],
            },
        ]

        created_count = 0
        updated_count = 0
        milestones_created = 0

        for data in projects_data:
            # Download and save image
            cover_photo = None
            if data.get("image_url"):
                try:
                    import requests
                    from django.core.files.base import ContentFile
                    from io import BytesIO

                    response = requests.get(data["image_url"], timeout=10)
                    if response.status_code == 200:
                        image_name = f"{data['name'].replace(' ', '-').lower()}.jpg"
                        cover_photo = ContentFile(response.content, name=image_name)
                        self.stdout.write(f"  📷 Downloaded image for: {data['name']}")
                except Exception as e:
                    self.stdout.write(f"  ⚠️ Could not download image for {data['name']}: {str(e)}")

            # Use get_or_create with name only — project_code auto-generates
            project, created = Project.objects.get_or_create(
                name=data["name"],
                defaults={
                    "description": data["description"],
                    "location": data["location"],
                    "county": data["county"],
                    "town": data["town"],
                    "start_date": data["start_date"],
                    "end_date": data.get("end_date"),
                    "budget": data["budget"],
                    "status": data["status"],
                    "is_archived": False,
                },
            )

            # Set cover photo if downloaded
            if cover_photo and created:
                project.cover_photo = cover_photo

            if created:
                if data.get("services"):
                    project.services.set(data["services"])
                project.save()
                self.stdout.write(f"  ✅ Created: {project.name} ({project.project_code})")
                created_count += 1
            else:
                project.description = data["description"]
                project.location = data["location"]
                project.county = data["county"]
                project.town = data["town"]
                project.start_date = data["start_date"]
                project.end_date = data.get("end_date")
                project.budget = data["budget"]
                project.status = data["status"]

                if cover_photo:
                    project.cover_photo = cover_photo
                project.save()
                if data.get("services"):
                    project.services.set(data["services"])
                self.stdout.write(f"  🔄 Updated: {project.name}")
                updated_count += 1

            # ---- Seed milestones (idempotent) ---------------------------
            # If this project already has milestones we don't recreate them;
            # this keeps re-runs safe and respects any manual edits.
            if not project.milestones.exists():
                created_in_loop = self._seed_milestones_for_project(project)
                milestones_created += created_in_loop

        # Final pass: re-aggregate progress on every project so the
        # stored `progress` field matches the milestone average.
        for project in Project.objects.filter(is_archived=False):
            project.update_progress()

        self.stdout.write(
            self.style.SUCCESS(
                f"\n✅ Projects seeding complete! "
                f"Projects created: {created_count}, updated: {updated_count}. "
                f"Milestones created: {milestones_created}."
            )
        )


    # =====================================================================
    # MILESTONE SCHEDULING
    # =====================================================================
    def _seed_milestones_for_project(self, project):
        """
        Generate a milestone schedule that matches the project's status.

        Status -> progress pattern:
          COMPLETED  -> 100% (all milestones done, completed in the past)
          ACTIVE     -> 30-75% (mix of completed + in-progress + pending,
                       randomly distributed)
          PLANNING   -> 0% (all pending, target dates in the near future)
          ON_HOLD    -> ~20% (first 1-2 milestones done, rest pending)
        """
        today = timezone.now().date()
        start = project.start_date
        end = project.end_date

        # Coerce string dates (from JSON / fixtures) into date objects
        if isinstance(start, str):
            start = parse_date(start) or today
        if isinstance(end, str):
            end = parse_date(end)

        # Decide how many milestones and which portion is "done" based on status
        if project.status == Project.Status.COMPLETED:
            milestones_to_seed = list(STANDARD_MILESTONES)
            completed_count = len(milestones_to_seed)
        elif project.status == Project.Status.ACTIVE:
            milestones_to_seed = list(STANDARD_MILESTONES)
            # Pick a random midpoint between 30% and 75%
            fraction = random.uniform(0.30, 0.75)
            completed_count = int(round(len(milestones_to_seed) * fraction))
        elif project.status == Project.Status.PLANNING:
            # Only seed first 3 milestones (still ahead of kickoff)
            milestones_to_seed = STANDARD_MILESTONES[:3]
            completed_count = 0
        elif project.status == Project.Status.ON_HOLD:
            milestones_to_seed = STANDARD_MILESTONES[:5]
            completed_count = 1
        else:
            return 0

        if not milestones_to_seed:
            return 0

        # Calculate target dates — distribute milestones evenly between
        # project start and end. If end is missing (still ongoing), project
        # out 18 months from start as a default horizon.
        if end:
            total_days = max((end - start).days, 30)
        else:
            total_days = 540  # ~18 months
            end = start + timedelta(days=total_days)

        step_days = max(total_days // max(len(milestones_to_seed), 1), 7)
        created = 0

        # If the project is ACTIVE/PLANNING and the milestone schedule is
        # mostly in the past, push unfinished target dates forward so the
        # dashboard shows a healthy mix (pending + in-progress) instead of
        # every remaining milestone flipping to OVERDUE. We anchor the
        # "in-progress now" milestone to today.
        active_projects_need_shift = (
            project.status in (Project.Status.ACTIVE, Project.Status.PLANNING, Project.Status.ON_HOLD)
            and (end < today)  # original schedule ended in the past
        )
        if active_projects_need_shift and completed_count < len(milestones_to_seed):
            # Rebuild target dates so the in-progress one sits on today and
            # later ones step forward from there.
            shift_start = today - timedelta(days=step_days * completed_count)
        else:
            shift_start = start

        for i, title in enumerate(milestones_to_seed):
            if active_projects_need_shift and i >= completed_count:
                target_date = shift_start + timedelta(days=step_days * (i + 1 - completed_count))
            else:
                target_date = start + timedelta(days=step_days * (i + 1))

            if i < completed_count:
                # Done — completion_percentage 100, completed_date before target
                completion_pct = 100
                completed_date = min(target_date, today - timedelta(days=1))
                status = Milestone.Status.COMPLETED
            else:
                # Not done — set a realistic partial completion if it's the
                # next-in-line on an ACTIVE project, otherwise 0
                if (
                    project.status == Project.Status.ACTIVE
                    and i == completed_count
                ):
                    completion_pct = random.randint(20, 60)
                    status = Milestone.Status.IN_PROGRESS
                else:
                    completion_pct = 0
                    completed_date = None
                    status = Milestone.Status.PENDING

            Milestone.objects.create(
                project=project,
                title=title,
                description=f"{title} phase for {project.name}.",
                target_date=target_date,
                completed_date=completed_date if i < completed_count else None,
                completion_percentage=completion_pct,
                status=status,
                order=i,
            )
            created += 1

        if created:
            self.stdout.write(
                f"    🚩 Seeded {created} milestones for {project.name}"
            )

        return created