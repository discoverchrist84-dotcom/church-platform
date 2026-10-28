import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = ("Create the first administrator from DJANGO_SUPERUSER_USERNAME / _EMAIL / _PASSWORD (for hosts with no terminal). "
            "Set ADMIN_RESET_PASSWORD=1 to set that password again for an existing user.")

    def handle(self, *args, **opts):
        username = os.environ.get("DJANGO_SUPERUSER_USERNAME", "")
        email = os.environ.get("DJANGO_SUPERUSER_EMAIL", "")
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD", "")
        if not (username and password and email):
            self.stdout.write("ensure_admin: no DJANGO_SUPERUSER_* variables set, skipping.")
            return
        User = get_user_model()
        user = User.objects.filter(username=username).first() or User.objects.filter(email__iexact=email).first()
        if user is None:
            User.objects.create_superuser(username=username, email=email, password=password)
            self.stdout.write(self.style.SUCCESS(f"Created administrator '{username}'."))
        elif os.environ.get("ADMIN_RESET_PASSWORD") == "1":
            user.set_password(password)
            user.is_staff = user.is_superuser = user.is_active = True
            user.save()
            self.stdout.write(self.style.SUCCESS(f"Password reset for '{username}'."))
        else:
            self.stdout.write(f"ensure_admin: '{username}' already exists.")
