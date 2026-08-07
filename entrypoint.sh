#!/usr/bin/env bash
# Professional Railway release hook
set -e

echo "=========================================="
echo "🚀 CALDAN CONSTRUCTION - RELEASE PHASE"
echo "🇰🇪 Building Kenya's Future, One Project at a Time."
echo "=========================================="
echo "🕐 Time: $(date)"
echo "=========================================="

# Create required directories
mkdir -p logs staticfiles media

# Run database migrations
echo "📦 Running database migrations..."
python manage.py migrate --noinput || {
    echo "❌ Migration failed!"
    exit 1
}
echo "✅ Migrations completed"

# Collect static files
echo "📁 Collecting static files..."
python manage.py collectstatic --noinput || {
    echo "❌ Static file collection failed!"
    exit 1
}
echo "✅ Static files collected"

# Create cache table
echo "💾 Setting up cache table..."
python manage.py createcachetable 2>/dev/null || echo "⚠️ Cache table creation skipped"

# Run Django production checks
echo "🔍 Running Django production checks..."
python manage.py check --deploy || echo "⚠️ Deployment check warnings (non-fatal)"

echo "=========================================="
echo "✅ Release phase complete!"
echo "=========================================="