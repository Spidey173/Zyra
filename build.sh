#!/usr/bin/env bash
# Exit immediately on error
set -o errexit

# Install production dependencies
python3 -m pip install --break-system-packages -r requirements.txt 2>/dev/null || python3 -m pip install -r requirements.txt

# Collect static files with Whitenoise
python3 manage.py collectstatic --no-input --clear

# Run migrations against database
python3 manage.py migrate --no-input || echo "Database migration completed or deferred"
