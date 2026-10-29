#!/bin/sh
# Start-up for Railway / Docker hosts. Safe to run on every deploy.
set -e
python manage.py collectstatic --noinput   # the CSS, JavaScript and images; harmless to repeat
python manage.py migrate --noinput
# Warn (in the deploy log) if a model changed but its migration file was not committed.
python manage.py makemigrations --check --dry-run >/dev/null 2>&1 || echo "WARNING: missing migration files. On your computer run: python manage.py makemigrations  then commit and push."
python manage.py ensure_admin
if [ "$RUN_IMPORT" = "1" ]; then
  # One-time loading of the church's districts and stations (set RUN_IMPORT=1, deploy once, then remove it).
  python manage.py import_stations
  python manage.py import_leaders
  python manage.py seed_books
fi
if [ -n "$LOADDATA" ]; then
  python manage.py loaddata $LOADDATA
fi
exec daphne -b 0.0.0.0 -p "${PORT:-8000}" config.asgi:application
