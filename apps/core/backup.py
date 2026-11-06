"""One-click backup of the website's data as a zip containing data.json (Django fixture format)."""
import io
import zipfile
from datetime import datetime

from django.core.management import call_command

# System tables that are rebuilt automatically and would clash when restoring.
EXCLUDE = ["contenttypes", "auth.permission", "sessions", "admin.logentry"]


def write_backup(fh):
    buf = io.StringIO()
    call_command("dumpdata", "--natural-foreign", "--natural-primary", "--indent", "1",
                 *[f"--exclude={e}" for e in EXCLUDE], stdout=buf)
    data = buf.getvalue().encode("utf-8")
    with zipfile.ZipFile(fh, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("data.json", data)
        z.writestr("README.txt", f"Church website backup made {datetime.now():%Y-%m-%d %H:%M}.\n"
                                  "To restore into an empty site: python manage.py migrate, then python manage.py loaddata data.json\n"
                                  "Pictures are inside data.json when the site stores them in the database. If your pictures are on a "
                                  "Railway Volume or S3, back those up separately.\n")
    return len(data)
