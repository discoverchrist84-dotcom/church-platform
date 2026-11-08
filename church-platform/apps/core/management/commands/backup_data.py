from django.core.management.base import BaseCommand

from apps.core.backup import write_backup


class Command(BaseCommand):
    help = "Save all the website's data (and uploaded pictures kept in the database) to one backup .zip file."

    def add_arguments(self, parser):
        parser.add_argument("output", nargs="?", default="church-backup.zip", help="File to write.")

    def handle(self, *args, output, **opts):
        with open(output, "wb") as fh:
            n = write_backup(fh)
        self.stdout.write(self.style.SUCCESS(f"Backup written to {output} ({n} bytes). Restore with: python manage.py loaddata data.json (inside the zip)."))
