"""
Development settings for Zyra project.
Optimized for local developer experience and testing.
"""

import os
from .base import *

# In development, DEBUG is enabled
DEBUG = True

# Development SECRET_KEY fallback
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-dev-only-secret-key-zyra-local-development-environment')

# ALLOWED_HOSTS from env, defaulting to localhost / loopback, strictly no '*'
_raw_hosts = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1,0.0.0.0')
ALLOWED_HOSTS = [h.strip() for h in _raw_hosts.split(',') if h.strip() and h.strip() != '*']
if not ALLOWED_HOSTS:
    ALLOWED_HOSTS = ['localhost', '127.0.0.1']

# CSRF Trusted Origins in development
_raw_csrf = os.environ.get('CSRF_TRUSTED_ORIGINS', 'http://localhost:8000,http://127.0.0.1:8000')
CSRF_TRUSTED_ORIGINS = [origin.strip() for origin in _raw_csrf.split(',') if origin.strip()]

# Cookie security relaxed for local HTTP development
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_HTTPONLY = False
CSRF_COOKIE_SAMESITE = 'Lax'

# Channels Channel Layer: Redis if configured, otherwise InMemoryChannelLayer
REDIS_URL = os.environ.get('REDIS_URL') or os.environ.get('REDIS_TLS_URL')
if REDIS_URL:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {
                "hosts": [REDIS_URL],
            },
        },
    }
else:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer"
        }
    }

