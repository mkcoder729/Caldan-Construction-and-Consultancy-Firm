#!/usr/bin/env bash
# Professional Railway release hook with selective seeding
set -e

echo "=========================================="
echo "🚀 CALDAN CONSTRUCTION - RELEASE PHASE"
echo "🇰🇪 Building Kenya's Future, One Project at a Time."
echo "=========================================="
echo "🕐 Time: $(date)"
echo "=========================================="

# Create required directories
mkdir -p logs staticfiles media

# ============================================================================
# DATABASE MIGRATIONS
# ============================================================================
echo "📦 Running database migrations..."
python manage.py migrate --noinput || {
    echo "❌ Migration failed!"
    exit 1
}
echo "✅ Migrations completed"

# ============================================================================
# COLLECT STATIC FILES
# ============================================================================
echo "📁 Collecting static files..."
python manage.py collectstatic --noinput || {
    echo "❌ Static file collection failed!"
    exit 1
}
echo "✅ Static files collected"

# ============================================================================
# CREATE CACHE TABLE
# ============================================================================
echo "💾 Setting up cache table..."
python manage.py createcachetable 2>/dev/null || echo "⚠️ Cache table creation skipped"

# ============================================================================
# REDIS CONNECTION CHECK
# ============================================================================
echo "🔍 Checking Redis connection..."
python manage.py shell -c "
import redis
import os
try:
    url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    r = redis.from_url(url)
    r.ping()
    print('✅ Redis is connected and working!')
except Exception as e:
    print(f'⚠️ Redis connection failed: {e}')
    print('⚠️ Celery tasks will not work without Redis!')
" || echo "⚠️ Redis check skipped"

# ============================================================================
# SEED DATA (Only on first deploy)
# ============================================================================
echo "🌱 Checking if seed data is needed..."

# Check if services exist
SERVICE_COUNT=$(python manage.py shell -c "from services.models import Service; print(Service.objects.count())" 2>/dev/null || echo "0")

if [ "$SERVICE_COUNT" -eq "0" ]; then
    echo "🌱 No data found. Running seed scripts for initial content..."

    echo "  📌 Seeding services..."
    python manage.py seed_services || echo "⚠️ Services seed skipped"

    echo "  📌 Seeding projects..."
    python manage.py seed_projects || echo "⚠️ Projects seed skipped"

    echo "  📌 Seeding team members..."
    python manage.py seed_team || echo "⚠️ Team seed skipped"

    echo "  📌 Seeding testimonials..."
    python manage.py seed_testimonials || echo "⚠️ Testimonials seed skipped"

    echo "  📌 Seeding blog posts..."
    python manage.py seed_blog || echo "⚠️ Blog seed skipped"

    echo "✅ Initial seed data completed!"
else
    echo "ℹ️ Data already exists. Skipping seed to avoid duplicates."
fi

# ============================================================================
# RUN DJANGO CHECKS
# ============================================================================
echo "🔍 Running Django production checks..."
python manage.py check --deploy || echo "⚠️ Deployment check warnings (non-fatal)"

echo "=========================================="
echo "✅ Release phase complete!"
echo "=========================================="