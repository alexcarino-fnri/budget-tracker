"""
Django settings for Budget Tracker project.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env file
load_dotenv(BASE_DIR / '.env')

# Security settings
SECRET_KEY = os.getenv(
    'SECRET_KEY',
    'django-insecure-local-budget-tracker-super-secret-key-change-in-prod-1234567890'
)

DEBUG = os.getenv('DEBUG', 'True').lower() in ('true', '1', 't')

allowed_hosts_raw = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1')
ALLOWED_HOSTS = [host.strip() for host in allowed_hosts_raw.split(',') if host.strip()]

csrf_trusted_raw = os.getenv(
    'CSRF_TRUSTED_ORIGINS',
    'https://*.trycloudflare.com,https://*.loca.lt,http://localhost:8000,http://127.0.0.1:8000,http://192.168.1.18:8000'
)
CSRF_TRUSTED_ORIGINS = [origin.strip() for origin in csrf_trusted_raw.split(',') if origin.strip()]

# Render deployment auto-detection & support
RENDER_EXTERNAL_HOSTNAME = os.getenv('RENDER_EXTERNAL_HOSTNAME')
if RENDER_EXTERNAL_HOSTNAME:
    if RENDER_EXTERNAL_HOSTNAME not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)
    origin = f"https://{RENDER_EXTERNAL_HOSTNAME}"
    if origin not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(origin)

if os.getenv('RENDER'):
    if '.onrender.com' not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append('.onrender.com')
    if 'https://*.onrender.com' not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append('https://*.onrender.com')

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
if not DEBUG and os.getenv('RENDER'):
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',

    # Custom apps
    'accounts',
    'wallets',
    'transactions',
    'budgets',
    'debts',
    'reports',
    'core',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

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
                'core.context_processors.global_finance_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Database configuration
# Supports local SQLite or cloud PostgreSQL (Render, Neon, Supabase, OCI)
database_url = os.getenv('DATABASE_URL')
if database_url:
    try:
        import dj_database_url
        DATABASES = {
            'default': dj_database_url.parse(
                database_url,
                conn_max_age=600,
                conn_health_checks=True,
            )
        }
    except ImportError:
        import urllib.parse
        url = urllib.parse.urlparse(database_url)
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.postgresql',
                'NAME': url.path[1:],
                'USER': urllib.parse.unquote_plus(url.username or ''),
                'PASSWORD': urllib.parse.unquote_plus(url.password or ''),
                'HOST': url.hostname,
                'PORT': str(url.port or '5432'),
            }
        }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Manila'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage',
    },
}

# Media uploads (receipts, etc.)
MEDIA_URL = '/media/'
MEDIA_ROOT = Path(os.getenv('MEDIA_ROOT', str(BASE_DIR / 'media')))

# Authentication URLs
LOGIN_URL = 'accounts:login'
LOGIN_REDIRECT_URL = 'core:dashboard'
LOGOUT_REDIRECT_URL = 'accounts:login'

# Dev Email Backend (Console)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Application specific settings
DEFAULT_CURRENCY = os.getenv('DEFAULT_CURRENCY', 'PHP')
DEFAULT_CURRENCY_SYMBOL = '₱'
