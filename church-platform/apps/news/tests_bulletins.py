from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.churches.models import Branch, BranchLeader, Membership
from apps.leadership.models import Council, CouncilMember
from apps.news.models import Bulletin

L = Branch.Level


class TenureTests(TestCase):
    def test_minister_transfer_date_is_four_years(self):
        b = Branch.objects.create(name="Hill Station", level=L.STATION)
        m = BranchLeader.objects.create(branch=b, name="Rev A", role="pastor", posted_on=date(2020, 1, 10))
        self.assertEqual(m.transfer_due_on, date(2024, 1, 10))
        self.assertEqual(m.posting_status, "overdue")
        m.is_current = False
        m.save()
        self.assertIsNotNone(m.ended_on)

    def test_council_term(self):
        c = Council.objects.create(name="General Council")
        mem = CouncilMember.objects.create(council=c, name="X", elected_on=date(2020, 5, 1))
        self.assertEqual(mem.term_ends_on, date(2024, 5, 1))
        self.assertEqual(mem.election_status, "term ended")
        self.assertEqual(mem.tenure, "2020–2024")


class BulletinTests(TestCase):
    def setUp(self):
        self.area = Branch.objects.create(name="Area 1", level=L.AREA)
        self.district = Branch.objects.create(name="Aba District", level=L.DISTRICT, parent=self.area)
        self.station = Branch.objects.create(name="Ehi Station", level=L.STATION, parent=self.district)
        User = get_user_model()
        self.member = User.objects.create_user("m", password="pw12345!x")
        self.other = User.objects.create_user("o", password="pw12345!x")
        Membership.objects.create(user=self.member, branch=self.station)

    def test_targeting_and_visibility(self):
        everyone = Bulletin.objects.create(title="All", body="x")
        chosen = Bulletin.objects.create(title="Area only", body="x", audience="chosen", send_notification=False)
        chosen.units.add(self.area)
        self.assertEqual(set(Bulletin.visible_to(self.member)), {everyone, chosen})
        self.assertEqual(set(Bulletin.visible_to(self.other)), {everyone})
        self.assertEqual(list(chosen.recipients()), [self.member])

    def test_notifies_once(self):
        b = Bulletin.objects.create(title="Hello", body="x")
        first = b.send_notifications()
        self.assertGreaterEqual(first, 2)
        b.refresh_from_db()
        self.assertEqual(b.send_notifications(), 0)

    def test_pages(self):
        Bulletin.objects.create(title="Hello", body="x", send_notification=False)
        self.assertContains(self.client.get(reverse("news:bulletins")), "Hello")
