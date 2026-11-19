"""
Production settings for Zyra project.
Strict security configurations, HTTPS enforcement, and fail-fast startup checks.
"""

import os
from django.core.exceptions import ImproperlyConfigured
from .base import *

# Strict production debug: always False
DEBUG = False

# 1. SECRET_KEY must come from environment; crash on startup if missing
SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY or SECRET_KEY.startswith('django-insecure-'):
    raise ImproperlyConfigured(
        "CRITICAL: A secure SECRET_KEY environment variable is required in production."
    )

# 2. ALLOWED_HOSTS from environment; strictly no '*'
_raw_hosts = os.environ.get('ALLOWED_HOSTS', '')
ALLOWED_HOSTS = [h.strip() for h in _raw_hosts.split(',') if h.strip() and h.strip() != '*']
if not ALLOWED_HOSTS:
    raise ImproperlyConfigured(
        "CRITICAL: ALLOWED_HOSTS environment variable is required in production and cannot be empty or '*'."
    )

# 3. CSRF Trusted Origins
_raw_csrf = os.environ.get('CSRF_TRUSTED_ORIGINS', '')
CSRF_TRUSTED_ORIGINS = [origin.strip() for origin in _raw_csrf.split(',') if origin.strip()]

# 4. HTTPS, Proxy, and Security Headers
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True
USE_X_FORWARDED_PORT = True

SECURE_SSL_REDIRECT = os.environ.get('SECURE_SSL_REDIRECT', 'True').lower() in ('true', '1', 'yes')
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# HTTP Strict Transport Security (HSTS)
SECURE_HSTS_SECONDS = int(os.environ.get('SECURE_HSTS_SECONDS', 31536000))  # 1 year default
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# 5. Cookie Security Settings
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_HTTPONLY = False  # Allows frontend JavaScript to read CSRF token for AJAX requests
CSRF_COOKIE_SAMESITE = 'Lax'

# 6. Channel Layer (WebSockets): Require REDIS_URL in production
REDIS_URL = os.environ.get('REDIS_URL') or os.environ.get('REDIS_TLS_URL')
if not REDIS_URL:
    raise ImproperlyConfigured(
        "CRITICAL: REDIS_URL environment variable is required in production for channels_redis. "
        "InMemoryChannelLayer is not permitted when DEBUG=False."
    )

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [REDIS_URL],
        },
    },
}

