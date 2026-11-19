"""
Base settings for Zyra project.
Shared configuration inherited by dev and prod environments.
"""

from pathlib import Path
import os
import dj_database_url

# BASE_DIR is 3 levels up: config/settings/base.py -> config/settings -> config -> BASE_DIR
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Load environment variables from .env file if present
_env_path = BASE_DIR / '.env'
if _env_path.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(_env_path)
    except ImportError:
        pass
    try:
        with open(_env_path, 'r', encoding='utf-8') as _f:
            for _line in _f:
                _line = _line.strip()
                if _line and not _line.startswith('#'):
                    _key, _val = None, None
                    if '=' in _line:
                        _key, _val = _line.split('=', 1)
                    elif ':' in _line:
                        _key, _val = _line.split(':', 1)
                    if _key and _val is not None:
                        _key = _key.strip()
                        _val = _val.strip().strip('"\'')
                        if _key and _key not in os.environ:
                            os.environ[_key] = _val
    except Exception:
        pass

# Application Branding
APP_NAME = os.environ.get('APP_NAME', 'Zyra')

# Default DEBUG is False for security
DEBUG = False

# Application definition
INSTALLED_APPS = [
    'daphne',
    'channels',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'storages',
    'core',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'core.middleware.UpdateLastSeenMiddleware',
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
                'core.context_processors.app_settings',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

AUTHENTICATION_BACKENDS = [
    'core.backends.CaseInsensitiveModelBackend',
    'django.contrib.auth.backends.ModelBackend',
]

# Database configuration
DATABASES = {
    'default': dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=600,
        conn_health_checks=True,
    )
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
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
WHITENOISE_MAX_AGE = 31536000

# Media Files Storage
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'home'
LOGOUT_REDIRECT_URL = 'landing'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Cloudinary Storage Configuration
CLOUDINARY_URL = os.environ.get('CLOUDINARY_URL')
if CLOUDINARY_URL and 'cloudinary://' in CLOUDINARY_URL:
    try:
        _raw = CLOUDINARY_URL.replace('cloudinary://', '')
        _creds, _cloud_name = _raw.split('@')
        _api_key, _api_secret = _creds.split(':')
        os.environ.setdefault('CLOUDINARY_CLOUD_NAME', _cloud_name)
        os.environ.setdefault('CLOUDINARY_API_KEY', _api_key)
        os.environ.setdefault('CLOUDINARY_API_SECRET', _api_secret)
    except Exception:
        pass

CLOUDINARY_CLOUD_NAME = os.environ.get('CLOUDINARY_CLOUD_NAME', '')
CLOUDINARY_API_KEY = os.environ.get('CLOUDINARY_API_KEY', '')
CLOUDINARY_API_SECRET = os.environ.get('CLOUDINARY_API_SECRET', '')

# S3 / Cloudflare R2 Storage Configuration (via django-storages)
USE_S3 = os.environ.get('USE_S3', 'False').lower() in ('true', '1', 'yes') or bool(os.environ.get('AWS_STORAGE_BUCKET_NAME'))
AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
AWS_STORAGE_BUCKET_NAME = os.environ.get('AWS_STORAGE_BUCKET_NAME')
AWS_S3_ENDPOINT_URL = os.environ.get('AWS_S3_ENDPOINT_URL')
AWS_S3_CUSTOM_DOMAIN = os.environ.get('AWS_S3_CUSTOM_DOMAIN')
AWS_S3_REGION_NAME = os.environ.get('AWS_S3_REGION_NAME', 'auto')
AWS_DEFAULT_ACL = None
AWS_S3_FILE_OVERWRITE = False

if USE_S3 and AWS_STORAGE_BUCKET_NAME:
    DEFAULT_STORAGE_BACKEND = "storages.backends.s3boto3.S3Boto3Storage"
elif CLOUDINARY_CLOUD_NAME and CLOUDINARY_API_KEY and CLOUDINARY_API_SECRET:
    DEFAULT_STORAGE_BACKEND = "core.storage.CloudinaryMediaStorage"
else:
    DEFAULT_STORAGE_BACKEND = "django.core.files.storage.FileSystemStorage"

STORAGES = {
    "default": {
        "BACKEND": DEFAULT_STORAGE_BACKEND,
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}

# Caching Configuration (Redis in Production if available, else LocMemCache)
REDIS_URL = os.environ.get('REDIS_URL', os.environ.get('REDIS_TLS_URL'))
if REDIS_URL:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': REDIS_URL,
            'TIMEOUT': 300,
        }
    }
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'zyra-cache',
            'TIMEOUT': 300,
        }
    }
