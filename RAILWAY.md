# Deploying on Railway

## 1. Create the project
1. Push the code to GitHub (private repository).
2. On railway.com: **New Project → Deploy from GitHub repo** and pick the repository. Railway builds the `Dockerfile` automatically.
3. In the same project click **+ New → Database → Add PostgreSQL**. (Do not use SQLite on Railway: its disk is wiped on every deploy, so accounts and data would vanish.)

## 2. Variables (service → Variables)
| Variable | Value |
|---|---|
| `SECRET_KEY` | a long random text (generate one at https://djecrety.ir) |
| `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` (use the "Add reference" button and pick the Postgres service) |
| `DJANGO_SUPERUSER_USERNAME` | your admin username |
| `DJANGO_SUPERUSER_EMAIL` | your email |
| `DJANGO_SUPERUSER_PASSWORD` | a strong password (used to create the first admin on deploy) |
| `RUN_IMPORT` | `1` for the first deploy only: loads the districts and stations, then delete this variable |
| `MEDIA_ROOT` | `/data/media` |
| `PRIVATE_MEDIA_ROOT` | `/data/private_media` |

Do **not** set `DEBUG`. The Dockerfile already uses the production settings.

## 3. Keep uploaded pictures and e-books
Service → **Settings → Volumes → New Volume**, mount path `/data`. Without a volume, uploaded pictures disappear at every deploy.

## 4. Get your web address
Service → **Settings → Networking → Generate Domain**. The site trusts Railway's own addresses automatically, so signing in works.
Using your own domain (for example `yourchurch.org`)? Add these variables as well:
`ALLOWED_HOSTS=yourchurch.org,www.yourchurch.org` and `CSRF_TRUSTED_ORIGINS=https://yourchurch.org,https://www.yourchurch.org`

## If you cannot sign in
- **"CSRF verification failed"** → the address is not trusted: set `CSRF_TRUSTED_ORIGINS=https://YOUR-ADDRESS` exactly as shown in the browser.
- **"Bad Request (400)"** → add the address to `ALLOWED_HOSTS`.
- **"Wrong password" for a new admin** → set `ADMIN_RESET_PASSWORD=1` with the `DJANGO_SUPERUSER_*` variables, redeploy once, then remove `ADMIN_RESET_PASSWORD`.
- **"Too many attempts"** → wait 15 minutes or redeploy (the counter resets).
- **Users vanish after a deploy** → `DATABASE_URL` is not pointing to Postgres.
