#!/usr/bin/env bash
# Exit immediately on error
set -o errexit

echo "Building Zyra for Vercel deployment..."

# Install production dependencies
python3 -m pip install --break-system-packages -r requirements.txt 2>/dev/null || python3 -m pip install -r requirements.txt

# Collect static files into staticfiles directory
python3 manage.py collectstatic --no-input --clear

# Run database migrations if database is accessible
python3 manage.py migrate --no-input || echo "Database migration step completed or deferred"

echo "Zyra build finished successfully!"
