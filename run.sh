#!/usr/bin/env bash
# exit on error
set -o errexit

# If a local virtualenv exists, activate it
if [ -d ".venv" ]; then
  source .venv/bin/activate
elif [ -d "venv" ]; then
  source venv/bin/activate
fi

echo "Building Zyra..."
pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate
python seed_demo_data.py

echo "Starting Zyra development server..."
python manage.py runserver
