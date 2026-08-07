# ============================================================================
# CALDAN CONSTRUCTION - DOCKERFILE FOR RAILWAY
# Django 4.2.19 LTS - MySQL - Production
# "Building Kenya's Future, One Project at a Time."
# ============================================================================

# Use official Python image with Debian Bookworm
FROM python:3.11-slim-bookworm

# ============================================================================
# INSTALL SYSTEM DEPENDENCIES FOR MYSQLCLIENT
# ============================================================================
RUN apt-get update && apt-get install -y --no-install-recommends \
    # MySQL client development headers (required for mysqlclient)
    default-libmysqlclient-dev \
    # Build tools for compiling Python packages
    build-essential \
    # pkg-config for finding libraries
    pkg-config \
    # Clean up to reduce image size
    && rm -rf /var/lib/apt/lists/*

# ============================================================================
# ENVIRONMENT VARIABLES
# ============================================================================
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DJANGO_SETTINGS_MODULE=calsite.settings \
    PORT=8080

# ============================================================================
# APPLICATION SETUP
# ============================================================================
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Make entrypoint executable
RUN chmod +x entrypoint.sh

# ============================================================================
# COLLECT STATIC FILES
# ============================================================================
RUN python manage.py collectstatic --noinput || echo "Static collection will run on startup"

# ============================================================================
# HEALTH CHECK
# ============================================================================
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health/')" || exit 1

# ============================================================================
# START APPLICATION
# ============================================================================
ENTRYPOINT ["./entrypoint.sh"]