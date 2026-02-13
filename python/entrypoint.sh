#!/bin/sh
set -e
# Run migrations when DATABASE_URL is set (e.g. in Docker)
if [ -n "$DATABASE_URL" ]; then
  echo "Running database migrations..."
  alembic upgrade head || echo "Warning: migrations failed (database may not be ready yet)"
fi
# If a command was passed (e.g. python -m app.worker), run it; otherwise start the API
if [ $# -gt 0 ]; then
  exec "$@"
else
  exec uvicorn main:app --host "${HOST:-0.0.0.0}" --port "${PORT:-8000}"
fi
