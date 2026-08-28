#!/usr/bin/env bash
# Exit immediately on error
set -o errexit

# Install production dependencies
pip install -r requirements.txt

# Collect static files with Whitenoise
python manage.py collectstatic --no-input

# Run migrations against PostgreSQL
python manage.py migrate
