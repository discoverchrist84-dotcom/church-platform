from django.test import TestCase
from django.urls import reverse

from apps.churches.models import Branch


class SeoTests(TestCase):
    def test_robots_and_sitemap(self):
        Branch.objects.create(name="Hill Station", level=Branch.Level.STATION)
        r = self.client.get("/robots.txt")
        self.assertContains(r, "Disallow: /admin/")
        self.assertContains(r, "sitemap.xml")
        s = self.client.get(reverse("core:sitemap"))
        self.assertEqual(s.status_code, 200)
        self.assertContains(s, "hill-station")

    def test_home_has_tags_and_private_pages_noindex(self):
        home = self.client.get("/")
        self.assertContains(home, 'rel="canonical"')
        self.assertContains(home, "application/ld+json")
        self.assertContains(home, 'property="og:title"')
        login = self.client.get(reverse("accounts:login"))
        self.assertEqual(login["X-Robots-Tag"], "noindex, nofollow")

    def test_acronym_is_explained_to_search_engines(self):
        home = self.client.get("/")
        self.assertContains(home, "CAC84FC")
        self.assertContains(home, "alternateName")
        self.assertContains(home, "stands for Christ Ascension Church 1984 Foundation Constitution")


class HomeMembersTests(TestCase):
    def test_member_count_is_admin_only(self):
        from django.contrib.auth import get_user_model

        User = get_user_model()
        User.objects.create_user("plain", password="pw12345!x")
        User.objects.create_user("boss", password="pw12345!x", is_staff=True)
        self.assertNotContains(self.client.get("/"), "<span>Members")
        self.client.login(username="plain", password="pw12345!x")
        self.assertNotContains(self.client.get("/"), "<span>Members")
        self.client.login(username="boss", password="pw12345!x")
        self.assertContains(self.client.get("/"), "<span>Members")
