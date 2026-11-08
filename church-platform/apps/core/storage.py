"""Keep uploads in the database so they survive restarts on hosts with a throw-away disk.

Turn on with MEDIA_STORAGE=database (automatic on Render). Pictures, then, are stored in the same
Postgres database as everything else; nothing lives on the local disk. For very large libraries
use S3-compatible storage instead (AWS_STORAGE_BUCKET_NAME)."""
import mimetypes
from io import BytesIO

from django.core.files.base import File
from django.core.files.storage import Storage
from django.db import DatabaseError
from django.utils.deconstruct import deconstructible


@deconstructible
class DatabaseStorage(Storage):
    def __init__(self, prefix="", base_url="/media/"):
        self.prefix = prefix
        self.base_url = base_url

    def _key(self, name):
        return f"{self.prefix}{name}".replace("\\", "/")

    def _model(self):
        from apps.core.models import StoredFile

        return StoredFile

    def _open(self, name, mode="rb"):
        try:
            row = self._model().objects.only("content").get(name=self._key(name))
        except self._model().DoesNotExist:
            raise FileNotFoundError(name)
        return File(BytesIO(bytes(row.content)), name=name)

    def _save(self, name, content):
        data = content.read()
        key = self._key(name)
        ctype = mimetypes.guess_type(name)[0] or ""
        self._model().objects.update_or_create(
            name=key, defaults={"content": data, "size": len(data), "content_type": ctype})
        return name

    def exists(self, name):
        try:
            return self._model().objects.filter(name=self._key(name)).exists()
        except DatabaseError:  # table not created yet (migration missing): treat as "no picture", never crash a page
            return False

    def delete(self, name):
        self._model().objects.filter(name=self._key(name)).delete()

    def size(self, name):
        return self._model().objects.values_list("size", flat=True).get(name=self._key(name))

    def url(self, name):
        return self.base_url + str(name).lstrip("/")

    def listdir(self, path):
        return [], []


def private_database_storage():
    return DatabaseStorage(prefix="private/", base_url="")
