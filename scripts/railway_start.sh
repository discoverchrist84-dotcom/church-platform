#!/bin/sh
# Start-up for Railway / Docker hosts. Safe to run on every deploy.
set -e
python manage.py collectstatic --noinput   # the CSS, JavaScript and images; harmless to repeat
python manage.py migrate --noinput
python manage.py ensure_admin
if [ "$RUN_IMPORT" = "1" ]; then
  # One-time loading of the church's districts and stations (set RUN_IMPORT=1, deploy once, then remove it).
  python manage.py import_stations
  python manage.py seed_books
fi
exec daphne -b 0.0.0.0 -p "${PORT:-8000}" config.asgi:application
