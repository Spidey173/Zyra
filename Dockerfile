FROM python:3.12-slim

# Prevent Python from writing .pyc files and buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /app

# Install system dependencies (libpq for PostgreSQL, curl for health checks)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . /app/

# Collect static assets into staticfiles
RUN python manage.py collectstatic --noinput || true

# Run as non-root user for security
RUN useradd -u 1000 -m zyra && chown -R zyra:zyra /app
USER zyra

EXPOSE 8000

# Run ASGI application with Daphne on port 8000
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "config.asgi:application"]

