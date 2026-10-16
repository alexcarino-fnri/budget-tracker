#!/bin/sh
set -e

# If a postgres database is configured, wait until it is ready
if [ -n "$POSTGRES_HOST" ]; then
    echo "Waiting for PostgreSQL at $POSTGRES_HOST:${POSTGRES_PORT:-5432}..."
    while ! nc -z "$POSTGRES_HOST" "${POSTGRES_PORT:-5432}"; do
        sleep 0.5
    done
    echo "PostgreSQL is up and accepting connections!"
fi

echo "Applying database migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Starting server..."
exec "$@"
