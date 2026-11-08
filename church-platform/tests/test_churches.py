import pytest
from django.contrib.auth import get_user_model

from apps.churches.models import Branch, Membership
from apps.core.permissions import can_manage_branch

pytestmark = pytest.mark.django_db
User = get_user_model()


@pytest.fixture
def tree():
    region = Branch.objects.create(name="North Area", level=Branch.Level.AREA)
    district = Branch.objects.create(name="Hill District", parent=region, level=Branch.Level.DISTRICT)
    local = Branch.objects.create(name="Hill Station", parent=district, level=Branch.Level.STATION)
    return region, district, local


def test_slug_is_generated_and_unique():
    a = Branch.objects.create(name="Grace Chapel")
    b = Branch.objects.create(name="Grace Chapel")
    assert a.slug == "grace-chapel"
    assert b.slug == "grace-chapel-2"


def test_ancestors_nearest_first(tree):
    region, district, local = tree
    assert [b.pk for b in local.ancestors()] == [district.pk, region.pk]


def test_parent_admin_manages_descendants(tree):
    region, _, local = tree
    user = User.objects.create_user("pastor", "p@example.org", "pw-12345678")
    Membership.objects.create(user=user, branch=region, role=Membership.Role.ADMIN)
    assert can_manage_branch(user, local)


def test_leader_only_manages_own_branch(tree):
    region, _, local = tree
    user = User.objects.create_user("leader", "l@example.org", "pw-12345678")
    Membership.objects.create(user=user, branch=local, role=Membership.Role.LEADER)
    assert can_manage_branch(user, local)
    assert not can_manage_branch(user, region)


def test_plain_member_cannot_manage(tree):
    _, _, local = tree
    user = User.objects.create_user("member", "m@example.org", "pw-12345678")
    Membership.objects.create(user=user, branch=local)
    assert not can_manage_branch(user, local)


def test_branch_api_and_join(client, tree):
    _, _, local = tree
    assert client.get(f"/api/branches/{local.slug}").json()["name"] == "Hill Station"

    user = User.objects.create_user("joiner", "j@example.org", "pw-12345678")
    client.force_login(user)
    resp = client.post(f"/api/branches/{local.slug}/join")
    assert resp.status_code == 200
    assert Membership.objects.filter(user=user, branch=local).exists()


def test_announcement_requires_leader(client, tree):
    _, _, local = tree
    user = User.objects.create_user("member", "m@example.org", "pw-12345678")
    client.force_login(user)
    resp = client.post(
        f"/api/community/branches/{local.slug}/announcements",
        data={"title": "Hi", "body": "There"},
        content_type="application/json",
    )
    assert resp.status_code == 403
