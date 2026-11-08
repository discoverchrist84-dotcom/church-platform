"""Phase 2: community, sermons, giving pages, notifications, branding and theme."""
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from apps.churches.models import Branch, Membership
from apps.community.models import Announcement, Event, EventRSVP, Ministry, Post, PrayerRequest, Report
from apps.giving.models import Donation, Fund
from apps.media_library.embeds import embed_url
from apps.realtime.models import Notification
from apps.realtime.services import notify_many

pytestmark = pytest.mark.django_db
User = get_user_model()
PW = "pw-12345678"


@pytest.fixture(autouse=True)
def no_broker(monkeypatch):
    """Never touch a real Celery broker from tests."""
    monkeypatch.setattr("apps.community.views.notify_users.delay", lambda *a, **k: None)
    monkeypatch.setattr("apps.giving.services.send_donation_receipt.delay", lambda *a, **k: None)


@pytest.fixture
def branch():
    return Branch.objects.create(name="Central Branch")


def make_user(name, branch=None, role=Membership.Role.MEMBER):
    user = User.objects.create_user(name, f"{name}@example.org", PW)
    if branch is not None:
        Membership.objects.create(user=user, branch=branch, role=role)
    return user


@pytest.fixture
def member(branch):
    return make_user("member", branch)


@pytest.fixture
def other(branch):
    return make_user("other", branch)


@pytest.fixture
def leader(branch):
    return make_user("leader", branch, Membership.Role.LEADER)


@pytest.fixture
def outsider():
    return make_user("outsider")


def url(name, branch, **kw):
    return reverse(f"community:{name}", kwargs={"slug": branch.slug, **kw})


# ---------------------------------------------------------------- branding / theme
def test_home_shows_church_name_and_theme_switch(client):
    html = client.get("/").content.decode()
    assert "Christ Ascension Church" in html
    assert "Lifters Power Assembly" in html
    for choice in ("light", "dark", "system"):
        assert f'data-theme-choice="{choice}"' in html


def test_manifest_uses_church_name(client):
    data = client.get("/manifest.webmanifest").json()
    assert "Christ Ascension Church" in data["name"]
    assert data["theme_color"].lower() == "#0b2a5b"


# ---------------------------------------------------------------- join / leave
def test_join_and_leave_from_web(client, branch, outsider):
    client.force_login(outsider)
    assert client.post(reverse("churches:join", args=[branch.slug])).status_code == 302
    assert Membership.objects.filter(user=outsider, branch=branch, is_primary=True).exists()
    client.post(reverse("churches:leave", args=[branch.slug]))
    assert not Membership.objects.filter(user=outsider, branch=branch).exists()


def test_branch_overview_renders_for_everyone(client, branch):
    assert client.get(branch.get_absolute_url()).status_code == 200


# ---------------------------------------------------------------- members-only gate
def test_board_gate(client, branch, member, outsider):
    anon = client.get(url("board", branch))
    assert anon.status_code == 200 and "for members" in anon.content.decode()

    client.force_login(outsider)
    assert client.get(url("board", branch)).status_code == 403

    client.force_login(member)
    assert client.get(url("board", branch)).status_code == 200


def test_member_posts_and_comments(client, branch, member, other):
    client.force_login(member)
    resp = client.post(url("post_create", branch), {"title": "Hello", "body": "First post"})
    post = Post.objects.get()
    assert resp.status_code == 302 and post.author == member

    client.force_login(other)
    client.post(url("post_detail", branch, post_id=post.pk), {"body": "Welcome!"})
    assert post.comments.count() == 1


# ---------------------------------------------------------------- moderation
def test_only_leaders_can_hide(client, branch, member, other, leader):
    post = Post.objects.create(branch=branch, author=member, title="T", body="B")
    toggle = url("toggle_hidden", branch, kind="post", pk=post.pk)

    client.force_login(other)
    assert client.post(toggle).status_code == 403
    post.refresh_from_db()
    assert not post.is_hidden

    client.force_login(leader)
    client.post(toggle)
    post.refresh_from_db()
    assert post.is_hidden


def test_hidden_post_is_404_for_members_but_visible_to_leaders(client, branch, member, other, leader):
    post = Post.objects.create(branch=branch, author=member, title="T", body="B", is_hidden=True)
    detail = url("post_detail", branch, post_id=post.pk)
    client.force_login(other)
    assert client.get(detail).status_code == 404
    client.force_login(leader)
    assert client.get(detail).status_code == 200


def test_report_flow(client, branch, member, other, leader):
    post = Post.objects.create(branch=branch, author=member, title="Bad", body="Spam spam")
    client.force_login(other)
    client.post(url("report", branch, kind="post", pk=post.pk), {"reason": "This is spam"})
    report = Report.objects.get()
    assert report.post == post and not report.resolved

    # reporting twice doesn't pile up duplicates
    client.post(url("report", branch, kind="post", pk=post.pk), {"reason": "again please"})
    assert Report.objects.count() == 1

    client.force_login(leader)
    assert "This is spam" in client.get(url("moderation", branch)).content.decode()
    client.post(url("resolve_report", branch, report_id=report.pk, action="hide"))
    post.refresh_from_db()
    report.refresh_from_db()
    assert post.is_hidden and report.resolved and report.resolved_by == leader


def test_members_cannot_open_moderation(client, branch, member):
    client.force_login(member)
    assert client.get(url("moderation", branch)).status_code == 403


# ---------------------------------------------------------------- prayer wall
def test_anonymous_prayer_hides_name(client, branch, member, other):
    PrayerRequest.objects.create(branch=branch, author=member, body="Please pray", is_anonymous=True)
    client.force_login(other)
    html = client.get(url("prayer", branch)).content.decode()
    card = html.split('<article class="prayer', 1)[1].split("</article>", 1)[0]
    assert "Please pray" in card and "Anonymous" in card
    assert "member" not in card.lower()


def test_prayer_answered_only_by_author(client, branch, member, other):
    req = PrayerRequest.objects.create(branch=branch, author=member, body="x")
    answered = url("prayer_answered", branch, pk=req.pk)
    client.force_login(other)
    assert client.post(answered).status_code == 404
    client.force_login(member)
    client.post(answered)
    req.refresh_from_db()
    assert req.is_answered


# ---------------------------------------------------------------- groups
def test_groups_join_and_leave(client, branch, member):
    Ministry.objects.create(branch=branch, name="Choir", slug="choir")
    client.force_login(member)
    client.post(url("group_join", branch, ministry_slug="choir"))
    assert member.ministries.count() == 1
    client.post(url("group_leave", branch, ministry_slug="choir"))
    assert member.ministries.count() == 0


# ---------------------------------------------------------------- events & announcements
def test_leader_creates_announcement_member_cannot(client, branch, member, leader):
    data = {"title": "Service moved", "body": "Now at 10", "is_pinned": "on"}
    client.force_login(member)
    assert client.post(url("announcement_create", branch), data).status_code == 403
    client.force_login(leader)
    assert client.post(url("announcement_create", branch), data).status_code == 302
    assert Announcement.objects.get().is_pinned


def test_event_rsvp_and_capacity(client, branch, member, other):
    event = Event.objects.create(branch=branch, title="Picnic", starts_at=timezone.now() + timedelta(days=2), capacity=1)
    rsvp = url("event_rsvp", branch, event_id=event.pk)
    client.force_login(member)
    client.post(rsvp, {"status": "going"})
    client.force_login(other)
    client.post(rsvp, {"status": "going"})  # full
    assert EventRSVP.objects.filter(event=event, status="going").count() == 1
    html = client.get(url("events", branch)).content.decode()
    assert "Picnic" in html and "Full" in html


def test_leader_creates_event(client, branch, leader):
    client.force_login(leader)
    start = (timezone.now() + timedelta(days=5)).strftime("%Y-%m-%dT%H:%M")
    resp = client.post(url("event_create", branch), {"title": "Revival", "starts_at": start})
    assert resp.status_code == 302 and Event.objects.filter(title="Revival").exists()


# ---------------------------------------------------------------- sermons
def test_sermons_page_public(client, branch):
    assert client.get(reverse("media_library:sermons", args=[branch.slug])).status_code == 200


def test_sermon_create_is_leader_only(client, branch, member, leader):
    page = reverse("media_library:sermon_create", args=[branch.slug])
    client.force_login(member)
    assert client.get(page).status_code == 403
    client.force_login(leader)
    resp = client.post(page, {"title": "Grace", "preached_on": "2026-10-18", "is_published": "on",
                              "video_url": "https://youtu.be/dQw4w9WgXcQ"})
    assert resp.status_code == 302
    assert "youtube-nocookie.com/embed/dQw4w9WgXcQ" in client.get(
        reverse("media_library:sermons", args=[branch.slug])
    ).content.decode()


@pytest.mark.parametrize(
    "link,expected",
    [
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"),
        ("https://youtu.be/dQw4w9WgXcQ", "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"),
        ("https://vimeo.com/123456", "https://player.vimeo.com/video/123456"),
        ("https://evil.example/watch?v=dQw4w9WgXcQ", ""),
        ("javascript:alert(1)", ""),
        ("", ""),
    ],
)
def test_embed_url(link, expected):
    assert embed_url(link) == expected


# ---------------------------------------------------------------- giving
def test_give_page_renders(client):
    Fund.objects.create(name="General", slug="general")
    assert client.get(reverse("giving:give")).status_code == 200


def test_give_flow_with_test_provider(client, settings):
    settings.DEBUG = True
    settings.PAYMENT_PROVIDER = "dummy"
    fund = Fund.objects.create(name="General", slug="general")

    resp = client.post(reverse("giving:give"), {"fund": fund.pk, "amount": "25.00", "donor_email": "d@example.org"})
    donation = Donation.objects.get()
    assert resp.status_code == 302 and "/give/dev-pay/" in resp["Location"]
    assert donation.status == Donation.Status.PENDING

    pay = reverse("giving:dev_pay", args=[donation.reference])
    assert client.get(pay).status_code == 200
    done = client.post(pay)
    donation.refresh_from_db()
    assert donation.status == Donation.Status.SUCCEEDED
    assert done.status_code == 302 and str(donation.reference) in done["Location"]
    assert "Thank you!" in client.get(done["Location"]).content.decode()


def test_dev_pay_unavailable_when_not_debug(client, settings):
    settings.DEBUG = False
    fund = Fund.objects.create(name="General", slug="general")
    d = Donation.objects.create(fund=fund, amount="5.00", provider="dummy")
    assert client.get(reverse("giving:dev_pay", args=[d.reference])).status_code == 404


def test_give_rejects_bad_amounts(client):
    fund = Fund.objects.create(name="General", slug="general")
    for bad in ("0", "-5", "abc"):
        resp = client.post(reverse("giving:give"), {"fund": fund.pk, "amount": bad})
        assert resp.status_code == 200
    assert Donation.objects.count() == 0


def test_giving_history_requires_login(client, member):
    assert client.get(reverse("giving:history")).status_code == 302
    client.force_login(member)
    assert client.get(reverse("giving:history")).status_code == 200


# ---------------------------------------------------------------- notifications
def test_notifications_need_login(client):
    assert client.get(reverse("realtime:list")).status_code == 302


def test_notification_open_and_read_all(client, member):
    notify_many([member], "Hello", "body", "/give/")
    note = Notification.objects.get()
    client.force_login(member)
    assert "Hello" in client.get(reverse("realtime:list")).content.decode()

    resp = client.get(reverse("realtime:open", args=[note.pk]))
    note.refresh_from_db()
    assert note.is_read and resp.status_code == 302 and resp["Location"] == "/give/"

    notify_many([member], "Two")
    client.post(reverse("realtime:read_all"))
    assert not Notification.objects.filter(user=member, is_read=False).exists()


def test_notification_open_ignores_offsite_urls(client, member):
    notify_many([member], "Phish", "", "https://evil.example/login")
    note = Notification.objects.get()
    client.force_login(member)
    resp = client.get(reverse("realtime:open", args=[note.pk]))
    assert resp["Location"] == reverse("realtime:list")
