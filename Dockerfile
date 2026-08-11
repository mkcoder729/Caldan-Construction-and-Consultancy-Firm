# ============================================================================
# CALDAN CONSTRUCTION - DOCKERFILE FOR RAILWAY
# Django 4.2.19 LTS - MySQL - Production
# Building Kenya's Future, One Project at a Time.
# ============================================================================

FROM python:3.11-slim-bookworm

# ============================================================================
# INSTALL SYSTEM DEPENDENCIES
# ============================================================================
RUN apt-get update && apt-get install -y --no-install-recommends \
    default-libmysqlclient-dev \
    build-essential \
    pkg-config \
    libnss3 \
    libatk-bridge2.0-0 \
    libdrm2 \
    libxkbcommon0 \
    libgbm1 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

# ============================================================================
# ENVIRONMENT VARIABLES
# ============================================================================
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DJANGO_SETTINGS_MODULE=calsite.settings \
    PORT=8080 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# ============================================================================
# APPLICATION SETUP
# ============================================================================
WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN playwright install chromium
RUN playwright install-deps

COPY . .

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