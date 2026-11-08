"""The administration area: every page opens, roles behave, settings take effect."""
import csv
import io

import pytest
from django.contrib import admin
from django.contrib.auth.models import Group
from django.urls import reverse

from apps.churches.models import Branch, BranchLeader
from apps.community.models import Post, Report
from apps.core.models import SiteSettings
from apps.core.roles import ADMIN_GROUP, EDITOR_GROUP, MODERATOR_GROUP, ensure_roles

pytestmark = pytest.mark.django_db
L = Branch.Level


@pytest.fixture
def hq():
    return Branch.objects.create(name="Head Area", level=L.AREA)


def _url(model, kind, *args):
    return reverse(f"admin:{model._meta.app_label}_{model._meta.model_name}_{kind}", args=args)


def test_dashboard_is_grouped_and_explains_itself(admin_client):
    r = admin_client.get(reverse("admin:index"))
    html = r.content.decode()
    assert r.status_code == 200
    for text in ("Church structure", "National councils", "Moderation", "Giving", "Website settings",
                 "Quick actions", "How adding, editing and deleting work"):
        assert text in html


def test_every_registered_model_has_working_pages(admin_client, hq):
    """List, search and add page for every model the admin knows about (what `check` cannot catch)."""
    assert len(admin.site._registry) >= 29
    for model in admin.site._registry:
        r = admin_client.get(_url(model, "changelist"), follow=True)
        assert r.status_code == 200, f"{model.__name__} list"
        r = admin_client.get(_url(model, "changelist"), {"q": "a"}, follow=True)
        assert r.status_code == 200, f"{model.__name__} search"
        r = admin_client.get(_url(model, "add"))
        assert r.status_code in (200, 403), f"{model.__name__} add"  # 403 only for the one-row settings page


def test_edit_and_delete_pages_explain_what_will_happen(admin_client, hq):
    area = Branch.objects.create(name="Lagos Area", level=L.AREA)
    BranchLeader.objects.create(branch=area, name="Rev. Ade", role="superintendent")
    edit = admin_client.get(_url(Branch, "change", area.pk)).content.decode()
    assert "Editing this" in edit and "Leaders" in edit
    delete = admin_client.get(_url(Branch, "delete", area.pk))
    html = delete.content.decode()
    assert delete.status_code == 200
    assert "Please read before you delete" in html and "Rev. Ade" in html  # lists what else goes
    # bulk delete confirmation carries the same warning
    r = admin_client.post(_url(Branch, "changelist"), {"action": "delete_selected", "_selected_action": [area.pk]})
    assert "Please read before you delete" in r.content.decode()


def test_site_settings_are_editable_and_show_on_the_website(admin_client, client):
    r = admin_client.get(_url(SiteSettings, "changelist"), follow=True)
    assert r.status_code == 200 and "Announcement banner" in r.content.decode()
    s = SiteSettings.load()
    s.brand, s.banner_is_active, s.banner_text = "Grace Cathedral", True, "Convention starts Friday"
    s.contact_phone, s.facebook_url, s.welcome_text = "+234 800 000", "https://facebook.com/graceit", "Welcome home"
    s.save()
    html = client.get(reverse("core:home")).content.decode()
    assert "Grace Cathedral" in html and "Convention starts Friday" in html
    assert "+234 800 000" in html and "facebook.com/graceit" in html and "Welcome home" in html
    s.banner_is_active = False
    s.save()
    assert "Convention starts Friday" not in client.get(reverse("core:home")).content.decode()
    assert client.get(reverse("core:manifest")).json()["name"]


def test_site_settings_is_a_single_undeletable_row(admin_client):
    assert SiteSettings.load().pk == SiteSettings.load().pk == 1
    SiteSettings.load().delete()
    assert SiteSettings.objects.count() == 1
    assert admin_client.get(_url(SiteSettings, "delete", 1)).status_code == 403


def test_export_to_spreadsheet_is_safe(admin_client, hq):
    Branch.objects.create(name="=HYPERLINK(\"http://evil\")", level=L.AREA)
    ids = list(Branch.objects.values_list("pk", flat=True))
    r = admin_client.post(_url(Branch, "changelist"), {"action": "export_csv", "_selected_action": ids})
    assert r["Content-Type"].startswith("text/csv")
    rows = list(csv.reader(io.StringIO(r.content.decode("utf-8-sig"))))
    assert rows[0][0] == "Name"
    assert any(row[0] == "National Headquarters" and "National Headquarters" in row for row in rows)  # level shown as a label, not a code
    assert not any("region" in row for row in rows)
    assert any(row[0].startswith("'=HYPERLINK") for row in rows)  # formulas are neutralised


def test_roles_have_the_right_reach(client, django_user_model, hq):
    ensure_roles()
    make = lambda name, group: django_user_model.objects.create_user(name, f"{name}@x.org", "pw-12345678", is_staff=True)  # noqa: E731
    boss, editor, mod = make("boss", ADMIN_GROUP), make("ed", EDITOR_GROUP), make("mod", MODERATOR_GROUP)
    boss.groups.add(Group.objects.get(name=ADMIN_GROUP))
    editor.groups.add(Group.objects.get(name=EDITOR_GROUP))
    mod.groups.add(Group.objects.get(name=MODERATOR_GROUP))

    client.force_login(boss)
    assert client.get(_url(Branch, "add")).status_code == 200
    assert client.get(_url(SiteSettings, "changelist"), follow=True).status_code == 200  # can change the website settings
    assert client.get(_url(Branch, "delete", hq.pk)).status_code == 200

    from apps.community.models import Event
    client.force_login(editor)
    assert client.get(_url(Event, "add")).status_code == 200
    assert client.get(_url(Branch, "add")).status_code == 403          # cannot restructure the church
    ev = Event.objects.create(branch=hq, title="Service", starts_at="2030-01-01T10:00:00Z")
    assert client.get(_url(Event, "delete", ev.pk)).status_code == 403  # editors add and edit, never delete

    client.force_login(mod)
    assert client.get(reverse("admin:index")).status_code == 200  # the dashboard adapts to what they may do
    assert client.get(_url(Report, "changelist")).status_code == 200
    assert client.get(_url(Post, "add")).status_code == 403
    assert client.get(_url(Event, "changelist")).status_code == 403


def test_ordinary_members_cannot_open_the_admin(client, django_user_model):
    u = django_user_model.objects.create_user("member", "m@x.org", "pw-12345678")
    client.force_login(u)
    r = client.get(reverse("admin:index"))
    assert r.status_code == 302 and "login" in r["Location"]


def test_give_and_remove_admin_access_from_the_users_page(admin_client, admin_user, django_user_model):
    u = django_user_model.objects.create_user("pastor", "p@x.org", "pw-12345678")
    url = _url(django_user_model, "changelist")
    admin_client.post(url, {"action": "make_church_admin", "_selected_action": [u.pk]})
    u.refresh_from_db()
    assert u.is_staff and not u.is_superuser and u.groups.filter(name=ADMIN_GROUP).exists()
    admin_client.post(url, {"action": "make_full_admin", "_selected_action": [u.pk]})
    u.refresh_from_db()
    assert u.is_superuser and u.is_staff
    admin_client.post(url, {"action": "remove_admin_access", "_selected_action": [u.pk]})
    u.refresh_from_db()
    assert not u.is_staff and not u.is_superuser
    # an administrator cannot lock themselves out
    admin_client.post(url, {"action": "remove_admin_access", "_selected_action": [admin_user.pk]})
    admin_user.refresh_from_db()
    assert admin_user.is_superuser
    admin_client.post(url, {"action": "deactivate", "_selected_action": [admin_user.pk]})
    admin_user.refresh_from_db()
    assert admin_user.is_active


def test_dashboard_flags_what_needs_attention(admin_client, hq, django_user_model):
    area = Branch.objects.create(name="Bare Area", level=L.AREA)
    member = django_user_model.objects.create_user("mm", "mm@x.org", "pw-12345678")
    post = Post.objects.create(branch=area, author=member, title="t", body="b")
    Report.objects.create(branch=area, reporter=member, post=post, reason="spam")
    html = admin_client.get(reverse("admin:index")).content.decode()
    assert "Needs your attention" in html
    assert "reports waiting for review" in html
    assert "without a superintendent" in html
