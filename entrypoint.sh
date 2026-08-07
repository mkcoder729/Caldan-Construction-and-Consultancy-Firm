#!/usr/bin/env bash
# Railway entrypoint - runs on every deploy
set -e

echo "=========================================="
echo "🚀 CALDAN CONSTRUCTION - PRODUCTION"
echo "🇰🇪 Building Kenya's Future, One Project at a Time."
echo "=========================================="
echo "📦 Environment: ${ENVIRONMENT:-production}"
echo "🕐 Time: $(date)"
echo "=========================================="

# Create logs directory if it doesn't exist
mkdir -p logs

# Run database migrations
echo "📦 Running database migrations..."
python manage.py migrate --noinput || {
    echo "❌ Migration failed! Check database connection."
    exit 1
}

# Collect static files
echo "📁 Collecting static files..."
python manage.py collectstatic --noinput || {
    echo "❌ Static file collection failed!"
    exit 1
}

# Create cache table if using database cache
echo "💾 Setting up cache table..."
python manage.py createcachetable || {
    echo "⚠️ Cache table creation skipped (may already exist)"
}

# Create superuser if no users exist (safely)
echo "👤 Checking for admin users..."
python manage.py shell -c "
from accounts.models import User
if not User.objects.filter(is_superuser=True).exists():
    print('⚠️ No admin user found. Create one via: python manage.py createsuperuser')
"

echo "=========================================="
echo "✅ Entrypoint complete! Starting Gunicorn..."
echo "=========================================="

# Start Gunicorn with production settings
exec gunicorn calsite.wsgi:application \
    --bind 0.0.0.0:$PORT \
    --workers 2 \
    --threads 4 \
    --worker-class gthread \
    --timeout 120 \
    --max-requests 1000 \
    --max-requests-jitter 50 \
    --access-logfile - \
    --error-logfile - \
    --log-level warning