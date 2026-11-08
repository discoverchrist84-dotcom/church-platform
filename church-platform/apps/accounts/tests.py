from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class DashboardTests(TestCase):
    def test_requires_login(self):
        r = self.client.get(reverse("accounts:dashboard"))
        self.assertEqual(r.status_code, 302)
        self.assertIn("login", r["Location"])

    def test_dashboard_and_navbar(self):
        get_user_model().objects.create_user("amaka", password="pass12345!x")
        self.client.login(username="amaka", password="pass12345!x")
        r = self.client.get(reverse("accounts:dashboard"))
        self.assertContains(r, "My books")
        self.assertContains(r, "My cart")
        home = self.client.get(reverse("core:home"))
        self.assertContains(home, "My account")
        self.assertNotContains(home, ">My books<")
