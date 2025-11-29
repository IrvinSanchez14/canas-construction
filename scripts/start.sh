#!/bin/bash

# Startup script for production deployment

set -e

echo "Starting Canas Construction API..."

# Run database migrations
echo "Running database migrations..."
alembic upgrade head

# Start the application
echo "Starting uvicorn server..."
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port ${PORT:-8000} \
    --workers ${WORKERS:-4} \
    --log-config logging.conf
