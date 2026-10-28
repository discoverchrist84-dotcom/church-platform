from django.core.files.base import ContentFile
from django.test import TestCase

from apps.core.storage import DatabaseStorage


class DatabaseStorageTests(TestCase):
    def test_round_trip(self):
        st = DatabaseStorage()
        name = st.save("councils/members/a.png", ContentFile(b"abc"))
        self.assertTrue(st.exists(name))
        self.assertEqual(st.open(name).read(), b"abc")
        self.assertEqual(st.url(name), "/media/" + name)
        st.delete(name)
        self.assertFalse(st.exists(name))
