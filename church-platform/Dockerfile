FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings.prod

WORKDIR /app

COPY requirements/ requirements/
RUN pip install --no-cache-dir -r requirements/prod.txt

COPY . .
RUN SECRET_KEY=build-only python manage.py collectstatic --noinput

EXPOSE 8000
# Runs database updates, creates the first admin (if asked), then starts Daphne on the host's $PORT
# (HTTP and WebSockets from one process).
CMD ["sh", "scripts/railway_start.sh"]
