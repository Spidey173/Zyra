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
if [ -f "seed_demo_data.py" ]; then
  python seed_demo_data.py
fi

echo "Starting Zyra development server..."
python manage.py runserver
