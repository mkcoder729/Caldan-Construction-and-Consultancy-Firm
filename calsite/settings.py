"""
Django settings for Caldan Construction project.
"""

import os
import sys
from pathlib import Path
from django.core.exceptions import ImproperlyConfigured

# Load .env file for local development. On Railway, real env vars win
# because Railway doesn't have a .env file.
try:
    from decouple import config, Csv
except ImportError:  # pragma: no cover
    # python-decouple missing — fall back to plain os.environ
    def config(key, default=None, cast=None, **kwargs):
        value = os.environ.get(key, default)
        if cast is bool:
            return str(value).lower() in ('true', '1', 'yes')
        if cast is int:
            return int(value) if value else 0
        if cast is float:
            return float(value) if value else 0.0
        if cast is Csv if False else None:  # noqa
            pass
        return value

    class Csv:  # noqa
        def __init__(self, *args, **kwargs):
            pass

        def __call__(self, value):
            return [v.strip() for v in str(value).split(',') if v.strip()]

# =====================================================================
# PATH CONFIGURATION
# =====================================================================
BASE_DIR = Path(__file__).resolve().parent.parent
APPS_DIR = BASE_DIR

# =====================================================================
# ENVIRONMENT VALIDATION
# =====================================================================
SECRET_KEY = config('SECRET_KEY', default='django-insecure-fallback-key-change-me')
DEBUG = config('DEBUG', default=False, cast=bool)

# =====================================================================
# ALLOWED_HOSTS - Professional Railway Configuration
# =====================================================================
# Start with safe defaults
ALLOWED_HOSTS = ['localhost', '127.0.0.1']

# Read ALLOWED_HOSTS from environment variable
allowed_hosts_env = os.environ.get('ALLOWED_HOSTS', '')
if allowed_hosts_env:
    # Split by comma and add each host
    for host in allowed_hosts_env.split(','):
        host = host.strip()
        if host:
            ALLOWED_HOSTS.append(host)

# Always add Railway domains (as a safety net)
ALLOWED_HOSTS.extend([
    '.railway.app',
    '.up.railway.app',
])

# Add the specific Railway public domain if it exists
railway_public = os.environ.get('RAILWAY_PUBLIC_DOMAIN', '')
if railway_public:
    ALLOWED_HOSTS.append(railway_public)

# Remove duplicates while preserving order
seen = set()
ALLOWED_HOSTS = [x for x in ALLOWED_HOSTS if not (x in seen or seen.add(x))]

# Debug: Print allowed hosts (only when DEBUG=True)
if DEBUG:
    print(f"🔍 ALLOWED_HOSTS: {ALLOWED_HOSTS}")

ENVIRONMENT = config('ENVIRONMENT', default='development')
IS_PRODUCTION = ENVIRONMENT == 'production'

# =====================================================================
# BASE URL
# =====================================================================
BASE_URL = config('BASE_URL', default='http://localhost:8000')
SITE_URL = config('SITE_URL', default='http://localhost:8000')

# =====================================================================
# APPLICATION DEFINITION
# =====================================================================
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'django_celery_beat',
    'django_celery_results',
    'crispy_forms',
    'crispy_bootstrap5',
    'widget_tweaks',
    'axes',
    'cloudinary',
    'cloudinary_storage',
    'django_extensions',
]

LOCAL_APPS = [
    'accounts',
    'website',
    'shop',
    'services',
    'dashboard',
    'projects',
    'inventory',
    'finances',
    'clients',
    'team',
    'reports',
    'notifications',
    'blog',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# =====================================================================
# MIDDLEWARE
# =====================================================================
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'axes.middleware.AxesMiddleware',
    'accounts.middleware.auth_middleware.AuthMiddleware',
    'accounts.middleware.otp_middleware.OTPMiddleware',
    'accounts.middleware.force_password_change_middleware.PasswordChangeRequiredMiddleware',
]

# =====================================================================
# ROOT URL CONFIG
# =====================================================================
ROOT_URLCONF = 'calsite.urls'
WSGI_APPLICATION = 'calsite.wsgi.application'
ASGI_APPLICATION = 'calsite.asgi.application'

# =====================================================================
# DATABASE CONFIGURATION - FIXED FOR RAILWAY
# =====================================================================
import urllib.parse as _urlparse

def _parse_mysql_url(url):
    """Parse a mysql:// URL into a Django DATABASES dict."""
    parsed = _urlparse.urlparse(url)
    return {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': (parsed.path or '/').lstrip('/'),
        'USER': _urlparse.unquote(parsed.username or ''),
        'PASSWORD': _urlparse.unquote(parsed.password or ''),
        'HOST': parsed.hostname or 'localhost',
        'PORT': str(parsed.port or '3306'),
        'OPTIONS': {
            'charset': 'utf8mb4',
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
        },
        'CONN_MAX_AGE': 300,  # Reduced from 600 to save memory
        'CONN_HEALTH_CHECKS': True,
    }

# Try multiple possible environment variable names
_db_url = (
    os.environ.get('DATABASE_URL', '') or
    os.environ.get('MYSQL_URL', '') or
    os.environ.get('CLEARDB_DATABASE_URL', '')
).strip()

if _db_url:
    # Railway: parse the auto-injected connection URL
    DATABASES = {'default': _parse_mysql_url(_db_url)}
    print(f"✅ Using database from URL: {_db_url.split('@')[0]}@...")
else:
    # Local dev: read individual DB_* vars from .env
    print("ℹ️ No DATABASE_URL found, using individual DB_* variables")
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': config('DB_NAME', default='caldan_construction'),
            'USER': config('DB_USER', default='root'),
            'PASSWORD': config('DB_PASSWORD', default=''),
            'HOST': config('DB_HOST', default='localhost'),
            'PORT': config('DB_PORT', default='3306'),
            'OPTIONS': {
                'charset': 'utf8mb4',
                'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            },
            'CONN_MAX_AGE': 300,
            'CONN_HEALTH_CHECKS': True,
        }
    }

# =====================================================================
# DATABASE ROUTING
# =====================================================================
DATABASE_ROUTERS = ['calsite.db_router.CaldanRouter']

# =====================================================================
# CACHE CONFIGURATION - MEMORY OPTIMIZED
# =====================================================================
REDIS_URL = config('REDIS_URL', default='redis://localhost:6379/0')

try:
    CACHES = {
        'default': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': REDIS_URL,
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient',
                'PARSER_CLASS': 'redis.connection.DefaultParser',
                'CONNECTION_POOL_CLASS': 'redis.BlockingConnectionPool',
                'CONNECTION_POOL_CLASS_KWARGS': {
                    'max_connections': 20,  # Reduced from 50 to save memory
                    'timeout': 10,  # Reduced from 20
                },
                'MAX_CONNECTIONS': 100,  # Reduced from 1000
                'PICKLE_VERSION': -1,
                'DEFAULT_TIMEOUT': 60,  # Reduced from 300 to save memory
            },
            'KEY_PREFIX': 'caldan',
        }
    }
except Exception:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
            'LOCATION': 'cache_table',
            'TIMEOUT': 60,
        }
    }

# =====================================================================
# SESSION CONFIGURATION
# =====================================================================
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_AGE = 2592000
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = config('SESSION_COOKIE_SECURE', default=False, cast=bool)
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_SAVE_EVERY_REQUEST = True
SESSION_COOKIE_NAME = 'caldan_session'

# =====================================================================
# TEMPLATES - MEMORY OPTIMIZED
# =====================================================================
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.template.context_processors.tz',
                'dashboard.context_processors.dashboard_context',
                'website.context_processors.trust_counter',
                'website.context_processors.site_settings',
                'website.context_processors.services_preview',
                'website.context_processors.cart_count',
                'website.context_processors.years_experience',
                'website.context_processors.project_stats',
            ],
            'debug': False,  # Always False in production
            # Cache template loaders for better performance
            'loaders': [
                ('django.template.loaders.cached.Loader', [
                    'django.template.loaders.filesystem.Loader',
                    'django.template.loaders.app_directories.Loader',
                ]),
            ] if IS_PRODUCTION else [
                'django.template.loaders.filesystem.Loader',
                'django.template.loaders.app_directories.Loader',
            ],
        },
    },
]

# =====================================================================
# CRISPY FORMS
# =====================================================================
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

# =====================================================================
# AUTHENTICATION
# =====================================================================
AUTH_USER_MODEL = 'accounts.User'
LOGIN_URL = 'accounts:login'
LOGIN_REDIRECT_URL = 'dashboard:overview'
LOGOUT_REDIRECT_URL = 'website:index'

AUTHENTICATION_BACKENDS = [
    'axes.backends.AxesStandaloneBackend',
    'django.contrib.auth.backends.ModelBackend',
]

# =====================================================================
# PASSWORD VALIDATION
# =====================================================================
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.BCryptSHA256PasswordHasher',
    'django.contrib.auth.hashers.BCryptPasswordHasher',
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
]

# =====================================================================
# CSRF & CORS
# =====================================================================
CSRF_COOKIE_SECURE = config('CSRF_COOKIE_SECURE', default=False, cast=bool)
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Lax'
CSRF_TRUSTED_ORIGINS = config('CSRF_TRUSTED_ORIGINS', default='http://localhost:8000', cast=Csv())

CORS_ALLOWED_ORIGINS = config('CORS_ALLOWED_ORIGINS', default='http://localhost:8000', cast=Csv())
CORS_ALLOW_CREDENTIALS = True

# =====================================================================
# AXES
# =====================================================================
AXES_ENABLED = True
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = 15
AXES_LOCKOUT_URL = '/accounts/account-locked/'
AXES_USERNAME_FORM_FIELD = 'email'

# =====================================================================
# OTP SETTINGS
# =====================================================================
OTP_EXPIRY_MINUTES = 5
OTP_MAX_ATTEMPTS = 3
OTP_RESEND_COOLDOWN_SECONDS = 60
OTP_MAX_RESENDS_PER_HOUR = 5
OTP_LENGTH = 8

# =====================================================================
# INTERNATIONALIZATION
# =====================================================================
LANGUAGE_CODE = 'en-ke'
TIME_ZONE = 'Africa/Nairobi'
USE_I18N = True
USE_TZ = True
USE_L10N = True

# =====================================================================
# STATIC FILES
# =====================================================================
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage' if not DEBUG else 'whitenoise.storage.CompressedStaticFilesStorage'

# =====================================================================
# MEDIA FILES
# =====================================================================
CLOUDINARY_CLOUD_NAME = config('CLOUDINARY_CLOUD_NAME', default='')
CLOUDINARY_API_KEY = config('CLOUDINARY_API_KEY', default='')
CLOUDINARY_API_SECRET = config('CLOUDINARY_API_SECRET', default='')

if CLOUDINARY_CLOUD_NAME and CLOUDINARY_API_KEY and CLOUDINARY_API_SECRET:
    DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'
    CLOUDINARY_STORAGE = {
        'CLOUD_NAME': CLOUDINARY_CLOUD_NAME,
        'API_KEY': CLOUDINARY_API_KEY,
        'API_SECRET': CLOUDINARY_API_SECRET,
        'SECURE': True,
        'EXIF_DISABLE': True,
    }
else:
    DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
    MEDIA_URL = '/media/'
    MEDIA_ROOT = BASE_DIR / 'media'

# =====================================================================
# EMAIL
# =====================================================================
RESEND_API_KEY = config('RESEND_API_KEY', default='')
SEND_REAL_EMAILS = config('SEND_REAL_EMAILS', default=False, cast=bool)
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='Caldan Construction <noreply@caldanconstruction.com>')
ADMIN_EMAIL = config('ADMIN_EMAIL', default='info.caldanconstruction@gmail.com')

# Resend does NOT expose SMTP — using smtp.resend.com silently fails.
# When SEND_REAL_EMAILS is True we route through our HTTP-API backend
# (calsite.backends.ResendEmailBackend). Otherwise Django prints to console.
if SEND_REAL_EMAILS and RESEND_API_KEY:
    EMAIL_BACKEND = 'calsite.backends.ResendEmailBackend'
    DEFAULT_FROM_EMAIL_REAL = DEFAULT_FROM_EMAIL
else:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# =====================================================================
# SMS
# =====================================================================
SMS_PROVIDER = config('SMS_PROVIDER', default='africastalking')
SEND_REAL_SMS = config('SEND_REAL_SMS', default=False, cast=bool)
AFRICASTALKING_API_KEY = config('AFRICASTALKING_API_KEY', default='')
AFRICASTALKING_USERNAME = config('AFRICASTALKING_USERNAME', default='sandbox')
AFRICASTALKING_SANDBOX = config('AFRICASTALKING_SANDBOX', default=True, cast=bool)

# =====================================================================
# PAYMENTS
# =====================================================================
PAYSTACK_SECRET_KEY = config('PAYSTACK_SECRET_KEY', default='')
PAYSTACK_PUBLIC_KEY = config('PAYSTACK_PUBLIC_KEY', default='')
PAYSTACK_LIVE = config('PAYSTACK_LIVE', default=False, cast=bool)
PAYSTACK_CALLBACK_URL = config('PAYSTACK_CALLBACK_URL', default='http://localhost:8000/shop/payment/verify/')
PAYSTACK_WEBHOOK_URL = config('PAYSTACK_WEBHOOK_URL', default='http://localhost:8000/shop/payment/webhook/')

MPESA_STK_PUSH_ENABLED = config('MPESA_STK_PUSH_ENABLED', default=True, cast=bool)
MPESA_BUSINESS_SHORTCODE = config('MPESA_BUSINESS_SHORTCODE', default='174379')
MPESA_PASSKEY = config('MPESA_PASSKEY', default='')
MPESA_CALLBACK_URL = config('MPESA_CALLBACK_URL', default='http://localhost:8000/shop/payment/mpesa-callback/')
MPESA_CONSUMER_KEY = config('MPESA_CONSUMER_KEY', default='')
MPESA_CONSUMER_SECRET = config('MPESA_CONSUMER_SECRET', default='')
MPESA_ENVIRONMENT = config('MPESA_ENVIRONMENT', default='sandbox')

# =====================================================================
# CELERY
# =====================================================================
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Africa/Nairobi'
CELERY_ENABLE_UTC = True
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60
CELERY_TASK_SOFT_TIME_LIMIT = 20 * 60
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'
CELERY_RESULT_EXPIRES = 86400
CELERY_TASK_ALWAYS_EAGER = DEBUG

# =====================================================================
# LOGGING - REDUCED FOR MEMORY
# =====================================================================
LOG_DIR = BASE_DIR / 'logs'
if not LOG_DIR.exists():
    LOG_DIR.mkdir(parents=True, exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {name} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {asctime} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'file_error': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOG_DIR / 'error.log',
            'maxBytes': 1024 * 1024 * 5,  # Reduced from 10MB
            'backupCount': 30,  # Reduced from 90
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file_error'],
            'level': config('DJANGO_LOG_LEVEL', default='WARNING'),  # Changed from INFO
            'propagate': False,
        },
        'caldan': {
            'handlers': ['console', 'file_error'],
            'level': config('LOG_LEVEL', default='WARNING'),  # Changed from INFO
            'propagate': False,
        },
    },
}

# =====================================================================
# SECURITY HEADERS
# =====================================================================
SECURE_SSL_REDIRECT = config('SECURE_SSL_REDIRECT', default=False, cast=bool)
SECURE_HSTS_SECONDS = config('SECURE_HSTS_SECONDS', default=0, cast=int)
SECURE_HSTS_INCLUDE_SUBDOMAINS = config('SECURE_HSTS_INCLUDE_SUBDOMAINS', default=False, cast=bool)
SECURE_HSTS_PRELOAD = config('SECURE_HSTS_PRELOAD', default=False, cast=bool)
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'

# =====================================================================
# REST FRAMEWORK
# =====================================================================
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': ('rest_framework.permissions.IsAuthenticated',),
    'DEFAULT_THROTTLE_CLASSES': (
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ),
    'DEFAULT_THROTTLE_RATES': {'anon': '100/day', 'user': '1000/hour'},
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

# =====================================================================
# SIMPLE JWT
# =====================================================================
from datetime import timedelta

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
}

# =====================================================================
# CALDAN SPECIFIC
# =====================================================================
CALDAN_OTP_EXPIRY_MINUTES = 5
CALDAN_GRACE_PERIOD_HOURS = 48
CALDAN_PROJECT_CODE_PREFIX = 'PRJ'
CALDAN_ORDER_CODE_PREFIX = 'ORD'
CALDAN_INVOICE_CODE_PREFIX = 'INV'

# =====================================================================
# AUDIT SETTINGS
# =====================================================================
AUDIT_LOG_RETENTION_DAYS = 365
AUDIT_LOG_HASH_ALGORITHM = 'SHA256'
AUDIT_REPORT_ENABLED = True
AUDIT_REPORT_FREQUENCY_DAYS = 14

# =====================================================================
# KENYA SETTINGS
# =====================================================================
CURRENCY_CODE = 'KES'
CURRENCY_SYMBOL = 'KSh'
CURRENCY_DECIMAL_PLACES = 2
CURRENCY_THOUSAND_SEPARATOR = ','
CURRENCY_DECIMAL_SEPARATOR = '.'

# =====================================================================
# ADMIN
# =====================================================================
ADMIN_SITE_HEADER = 'Caldan Construction and Consultancy Firm Administration'
ADMIN_SITE_TITLE = 'Caldan Construction and Consultancy Firm Admin'
ADMIN_INDEX_TITLE = 'Platform Administration'
ADMIN_URL = 'admin/'

# =====================================================================
# DEFAULT AUTO FIELD
# =====================================================================
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# =====================================================================
# PERFORMANCE OPTIMIZATIONS FOR RAILWAY FREE TIER
# =====================================================================

# Disable debug toolbar in production
if IS_PRODUCTION:
    # Remove debug toolbar if present
    if 'debug_toolbar' in INSTALLED_APPS:
        INSTALLED_APPS.remove('debug_toolbar')

    # Reduce database connection pooling
    for db_config in DATABASES.values():
        db_config['CONN_MAX_AGE'] = 300

    # Disable unused middleware
    # Keep it simple - only remove if we're sure
    pass

# Print memory optimization status
if IS_PRODUCTION:
    print("🚀 Running in production mode with memory optimizations")
    print(f"📦 Workers: 2 (Gunicorn), Concurrency: 1 (Celery)")
    print(f"💾 Database pool: 300s, Cache timeout: 60s")