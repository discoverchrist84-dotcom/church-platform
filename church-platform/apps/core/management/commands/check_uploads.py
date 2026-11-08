from django.apps import apps
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import models


class Command(BaseCommand):
    help = "List every uploaded picture/file, its web address, and whether the file really exists on disk."

    def handle(self, *args, **opts):
        self.stdout.write(f"MEDIA_ROOT = {settings.MEDIA_ROOT}\nMEDIA_URL  = {settings.MEDIA_URL}\n"
                          f"Django serves uploads itself: {settings.DEBUG or settings.SERVE_MEDIA}\n")
        total = bad = 0
        for model in apps.get_models():
            for f in model._meta.get_fields():
                if not isinstance(f, models.FileField):
                    continue
                for obj in model.objects.exclude(**{f.name: ""}):
                    file = getattr(obj, f.name)
                    total += 1
                    ok = file.storage.exists(file.name)
                    bad += (not ok)
                    self.stdout.write(f"{'OK     ' if ok else 'MISSING'} {model.__name__}#{obj.pk}.{f.name} -> {file.url}")
        self.stdout.write(self.style.SUCCESS(f"{total} uploaded file(s), {bad} missing.") if not bad
                          else self.style.ERROR(f"{total} uploaded file(s), {bad} missing on disk. Upload those again in the admin."))
