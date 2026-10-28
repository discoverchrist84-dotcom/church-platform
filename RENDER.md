# Deploying on Render

The error `Could not open requirements file: requirements.txt` happened because Render used its plain
"Python" mode with the default command. This version fixes it in two ways. Use **either**:

## Option A (recommended): Docker
1. Push this version to GitHub.
2. Render → **New + → Blueprint** → choose the repository → **Apply**. It reads `render.yaml`, builds the `Dockerfile`
   (Python 3.13) and creates the Postgres database.
3. When asked, enter `DJANGO_SUPERUSER_USERNAME`, `DJANGO_SUPERUSER_EMAIL` and `DJANGO_SUPERUSER_PASSWORD`.
4. When it is live, open the address Render shows (`https://church-platform-xxxx.onrender.com`) and sign in.
5. Afterwards open the service → Environment and delete `RUN_IMPORT` (it only needs to run once).

## Option B: plain Python service
- **Build command:** `pip install -r requirements.txt && python manage.py collectstatic --noinput`
- **Start command:** `sh scripts/railway_start.sh`
- **Environment variables:** `PYTHON_VERSION=3.13.5`, `DJANGO_SETTINGS_MODULE=config.settings.prod`, `SECRET_KEY`, `DATABASE_URL`
  (from a Render Postgres: "Internal Database URL"), the three `DJANGO_SUPERUSER_*`, and `RUN_IMPORT=1` once.
- Python 3.14 does not work yet with some packages here, so keep it on 3.13.

## Good to know (free plan)
- The website **sleeps** after 15 minutes without visitors and takes about a minute to wake.
- The free Postgres database **expires after 30 days**: upgrade it before then or you lose the data.
- There is **no permanent disk** on the free plan, so uploaded pictures and e-books are lost at each deploy.
  Fix: a paid plan with a Disk mounted at `/data` (set `MEDIA_ROOT=/data/media`, `PRIVATE_MEDIA_ROOT=/data/private_media`),
  or Cloudflare R2 / S3 (set the `AWS_*` variables in `.env.example`).
- Signing in works automatically on `*.onrender.com`. For your own domain set `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS`
  (see RAILWAY.md, "Using your own domain").
