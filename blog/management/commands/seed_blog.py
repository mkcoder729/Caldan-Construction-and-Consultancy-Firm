"""
Seed command for Blog Posts - Caldan Construction
Creates sample blog posts with construction-related content.
"""

import io
import urllib.request
from django.core.management.base import BaseCommand
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.utils import timezone
from django.utils.text import slugify
from blog.models import BlogPost


def _download_to_uploadedfile(url, timeout=15):
    """Download an image and return an InMemoryUploadedFile.

    Cloudinary's descriptor needs a proper Django file object (with .name,
    .size, .read()), not a raw ContentFile — that's why this returns the
    richer InMemoryUploadedFile. Returns None on any network/HTTP error so
    the seeder never crashes.
    """
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read()
        if not data:
            return None
        # Filename from the URL path
        filename = url.split("/")[-1].split("?")[0] or "blog_image.jpg"
        if not filename.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
            filename += ".jpg"
        return InMemoryUploadedFile(
            file=io.BytesIO(data),
            field_name="image",
            name=filename,
            content_type="image/jpeg",
            size=len(data),
            charset=None,
        )
    except Exception:
        return None


class Command(BaseCommand):
    help = "Seed blog posts data into the database"

    def handle(self, *args, **options):
        self.stdout.write("🌱 Seeding blog posts...")

        blog_posts_data = [
            {
                "title": "The Future of Sustainable Construction in Kenya",
                "excerpt": "Exploring eco-friendly building practices and sustainable materials shaping Kenya's construction industry.",
                "content": """
Sustainable construction is no longer a trend — it's a necessity. As Kenya continues to urbanize rapidly, the construction industry faces increasing pressure to adopt environmentally responsible practices.

## Why Sustainability Matters

The construction sector accounts for approximately 40% of global carbon emissions. In Kenya, with our growing population and expanding cities, the need for sustainable building practices has never been more urgent.

## Key Sustainable Practices

### 1. Green Building Materials
Using locally sourced, recycled, and renewable materials reduces the carbon footprint of construction projects. Materials like bamboo, reclaimed timber, and recycled steel are becoming increasingly popular.

### 2. Energy Efficiency
Incorporating energy-efficient designs — from solar panels to natural ventilation systems — helps reduce long-term operational costs and environmental impact.

### 3. Water Conservation
Rainwater harvesting systems, greywater recycling, and water-efficient fixtures are essential for sustainable construction in Kenya.

## Caldan's Commitment

At Caldan Construction, we are committed to building a sustainable future. We incorporate green building practices into every project, from residential homes to commercial developments.

We believe that building Kenya's future means building responsibly — for our clients, our communities, and our planet.
                """,
                "category": BlogPost.Category.CONSTRUCTION,
                "is_published": True,
                "published_at": timezone.now() - timezone.timedelta(days=1),
                "image_url": "https://images.unsplash.com/photo-1541888946425-d81bb19240f5?w=800&q=80",
            },
            {
                "title": "5 Tips for Choosing the Right Construction Partner",
                "excerpt": "How to select a reliable construction company for your project — from credentials to communication.",
                "content": """
Choosing the right construction partner is one of the most important decisions you'll make for your project. Whether you're building a home, an office, or a commercial development, the right partner can make all the difference.

## 1. Check Credentials and Experience

Always verify that your construction partner is properly licensed and registered. Look for industry certifications and a proven track record of successful projects similar to yours.

## 2. Review Past Projects

A reputable construction company should have a portfolio of completed projects. Request references and, if possible, visit past project sites to see the quality of their work firsthand.

## 3. Communication is Key

Your construction partner should communicate clearly and regularly. They should be responsive to your questions and proactive about project updates.

## 4. Understand the Contract

Before signing anything, make sure you fully understand the scope of work, payment terms, timelines, and what happens if things change.

## 5. Trust Your Instincts

If something doesn't feel right, it probably isn't. Choose a partner you trust and feel comfortable working with.

At Caldan Construction, we pride ourselves on being a trusted partner for our clients. We're transparent, communicative, and committed to delivering excellence.
                """,
                "category": BlogPost.Category.CONSULTANCY,
                "is_published": True,
                "published_at": timezone.now() - timezone.timedelta(days=3),
                "image_url": "https://images.unsplash.com/photo-1504917595217-d4dc5ebe6122?w=800&q=80",
            },
            {
                "title": "Renovating Your Home? Here's What You Need to Know",
                "excerpt": "Essential tips for a successful home renovation — from planning to completion.",
                "content": """
Home renovations can be exciting and overwhelming in equal measure. Whether you're updating your kitchen, adding a room, or transforming your entire home, careful planning is essential.

## Planning Your Renovation

### 1. Define Your Goals
What do you want to achieve? More space? Modern finishes? Increased property value? Be clear about your objectives before you start.

### 2. Set a Realistic Budget
Renovations almost always cost more than expected. Set a budget and add a 15-20% contingency for unexpected expenses.

### 3. Choose the Right Team
From architects to contractors, the right team is crucial. Look for professionals with experience in your type of renovation.

## Common Mistakes to Avoid

- **Underestimating Costs** — Always overestimate your budget.
- **Skipping Permits** — Ensure all necessary permits are obtained.
- **Choosing Trends over Function** — Design for longevity, not just current trends.
- **Ignoring Energy Efficiency** — Invest in insulation, windows, and efficient systems.

## Why Choose Caldan?

With over a decade of experience in renovations across Kenya, Caldan Construction has transformed countless homes. Our team brings expertise, attention to detail, and a commitment to quality to every project.
                """,
                "category": BlogPost.Category.CONSTRUCTION,
                "is_published": True,
                "published_at": timezone.now() - timezone.timedelta(days=7),
                "image_url": "https://images.unsplash.com/photo-1580582932707-520aed937b7b?w=800&q=80",
            },
            {
                "title": "The Importance of Quality Materials in Construction",
                "excerpt": "Why cutting corners on materials is never worth it — and how to choose the right ones for your project.",
                "content": """
Quality materials are the foundation of any successful construction project. Whether you're building from the ground up or renovating an existing structure, the materials you choose determine the longevity, safety, and appearance of the final result.

## Why Quality Matters

### 1. Durability
High-quality materials last longer, reducing the need for frequent repairs or replacements.

### 2. Safety
Substandard materials can compromise the structural integrity of your building, putting occupants at risk.

### 3. Aesthetic Appeal
Premium materials look better and retain their appearance longer.

### 4. Cost Effectiveness
While quality materials may cost more upfront, they save money in the long run by reducing maintenance and replacement costs.

## How to Choose Quality Materials

- **Research** — Understand what you're buying. Research different brands and products.
- **Trust Your Builder** — A reputable builder will recommend quality materials.
- **Check Certifications** — Look for recognized certifications and standards.

## Caldan's Commitment

At Caldan Construction, we never compromise on quality. We source the best materials for every project and ensure they meet the highest standards.
                """,
                "category": BlogPost.Category.CONSULTANCY,
                "is_published": True,
                "published_at": timezone.now() - timezone.timedelta(days=14),
                "image_url": "https://images.unsplash.com/photo-1504307651254-35680f356dfd?w=800&q=80",
            },
            {
                "title": "Caldan Construction Completes 25-Unit Apartment Project in Nakuru",
                "excerpt": "A milestone achievement for Caldan Construction as we deliver 25 modern residential units in Nakuru.",
                "content": """
We are proud to announce the successful completion of a 25-unit apartment project in Nakuru — one of our largest residential developments to date.

## The Project

Located in the heart of Nakuru, this development features 25 modern residential apartments, each designed with comfort, functionality, and style in mind. The project includes:

- 2-bedroom and 3-bedroom units
- Spacious living areas
- Modern kitchens and bathrooms
- Secure parking
- Landscaped common areas

## Key Challenges

Every project presents unique challenges, and this one was no exception. From site preparation to weather delays, our team remained focused on delivering quality results.

## Client Feedback

"Caldan Construction delivered our project on time and within budget. Their professionalism and attention to detail was exceptional." — Kennedy Onyancha

## Looking Forward

This project represents our continued commitment to building Kenya's future, one project at a time. We're excited to take on more residential developments across the country.
                """,
                "category": BlogPost.Category.NEWS,
                "is_published": True,
                "published_at": timezone.now() - timezone.timedelta(days=5),
                "image_url": "https://images.unsplash.com/photo-1480074568708-e7b720bb3f09?w=800&q=80",
            },
            {
                "title": "Waterproofing 101: Protecting Your Building from Water Damage",
                "excerpt": "Understanding the importance of waterproofing and how to ensure your building stays dry.",
                "content": """
Water damage is one of the most common and costly issues facing building owners in Kenya. From roof leaks to basement flooding, water intrusion can compromise structural integrity and lead to expensive repairs.

## Why Waterproofing Matters

### 1. Structural Protection
Water infiltration can weaken foundations, cause corrosion, and lead to structural failure.

### 2. Health and Safety
Damp conditions promote mold growth, which can cause respiratory problems and other health issues.

### 3. Property Value
Buildings with effective waterproofing retain their value and appeal.

### 4. Cost Savings
Preventing water damage is significantly cheaper than repairing it.

## Types of Waterproofing

- **Roof Waterproofing** — Protects the building from rain and UV damage
- **Basement Waterproofing** — Prevents groundwater infiltration
- **Wall Waterproofing** — Protects walls from moisture ingress
- **Tank Waterproofing** — Ensures water storage structures remain watertight

## Caldan's Expertise

At Caldan Construction, we specialize in comprehensive waterproofing solutions for all types of buildings. Our team uses the latest materials and techniques to ensure your building stays dry and protected for years to come.
                """,
                "category": BlogPost.Category.CONSTRUCTION,
                "is_published": True,
                "published_at": timezone.now() - timezone.timedelta(days=10),
                "image_url": "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?w=800&q=80",
            },
            {
                "title": "Interior Design Trends for 2024 and Beyond",
                "excerpt": "Discover the latest interior design trends that are shaping Kenya's homes and offices.",
                "content": """
Interior design trends evolve constantly, but the best designs are those that combine style with functionality. Here are the top trends shaping Kenya's interior spaces in 2024.

## 1. Natural Materials
Wood, stone, and natural fibers continue to dominate, bringing warmth and texture to modern interiors.

## 2. Earth Tones
Neutral palettes — warm beiges, soft greens, and terracottas — are replacing stark whites and grays.

## 3. Multi-Functional Spaces
With more people working from home, spaces that serve multiple purposes are in high demand.

## 4. Statement Lighting
Unique light fixtures are becoming a focal point in many designs.

## 5. Indoor Plants
Biophilic design continues to be popular, with indoor plants bringing nature into living and working spaces.

## 6. Sustainable Design
Eco-friendly materials and furniture are no longer niche — they're becoming the standard.

## Caldan's Design Services

At Caldan Construction, we offer comprehensive interior design services. Our team works closely with you to create spaces that reflect your style and meet your needs.
                """,
                "category": BlogPost.Category.CONSTRUCTION,
                "is_published": True,
                "published_at": timezone.now() - timezone.timedelta(days=8),
                "image_url": "https://images.unsplash.com/photo-1497366216548-37526070297c?w=800&q=80",
            },
        ]

        created_count = 0
        updated_count = 0

        for data in blog_posts_data:
            slug = slugify(data["title"])

            post, created = BlogPost.objects.get_or_create(
                slug=slug,
                defaults={
                    "title": data["title"],
                    "excerpt": data["excerpt"],
                    "content": data["content"],
                    "category": data["category"],
                    "is_published": data["is_published"],
                    "published_at": data["published_at"],
                },
            )

            # Always sync non-image fields (so the seeder is idempotent).
            post.title = data["title"]
            post.excerpt = data["excerpt"]
            post.content = data["content"]
            post.category = data["category"]
            post.is_published = data["is_published"]
            post.published_at = data["published_at"]

            # Attach the image if the post has none yet. We only download/upload
            # when the field is empty so re-running the seeder doesn't churn
            # Cloudinary with duplicate uploads.
            image_url = data.get("image_url")
            if image_url and not post.image:
                image_file = _download_to_uploadedfile(image_url)
                if image_file:
                    # Cloudinary's descriptor wants a real Django file object.
                    post.image = image_file
                    self.stdout.write(f"  📷 Image attached: {post.title}")
                else:
                    self.stdout.write(
                        self.style.WARNING(f"  ⚠️  Image download failed: {post.title}")
                    )

            post.save()

            if created:
                self.stdout.write(f"  ✅ Created: {post.title}")
                created_count += 1
            else:
                self.stdout.write(f"  🔄 Updated: {post.title}")
                updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"\n✅ Blog seeding complete! Created: {created_count}, Updated: {updated_count}"
            )
        )