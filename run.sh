#!/usr/bin/env bash
# Exit immediately on error
set -o errexit

PORT="${PORT:-8000}"

# If a local virtualenv exists, activate it
if [ -d ".venv" ]; then
  source .venv/bin/activate
elif [ -d "venv" ]; then
  source venv/bin/activate
fi

echo "==> Preparing Zyra (ASGI + Django Channels)..."
pip install -r requirements.txt

echo "==> Running database migrations..."
python manage.py migrate --no-input

echo "==> Collecting static assets..."
python manage.py collectstatic --no-input

if [ -f "seed_demo_data.py" ]; then
  echo "==> Seeding demo data..."
  python seed_demo_data.py
fi

echo "==> Starting Zyra ASGI development server on port ${PORT}..."
# When 'daphne' is installed in INSTALLED_APPS, runserver runs the ASGI application with auto-reloading
python manage.py runserver "0.0.0.0:${PORT}"
