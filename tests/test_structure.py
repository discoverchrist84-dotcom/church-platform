import io

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import Image

from apps.churches.models import Branch
from apps.leadership.models import Council, CouncilMember

pytestmark = pytest.mark.django_db
L = Branch.Level


@pytest.fixture
def chain():
    area = Branch.objects.create(name="Lagos Area", level=L.AREA)
    d1 = Branch.objects.create(name="Ikeja District", parent=area, level=L.DISTRICT)
    d2 = Branch.objects.create(name="Yaba District", parent=area, level=L.DISTRICT)
    s1 = Branch.objects.create(name="Allen Station", parent=d1, level=L.STATION)
    s2 = Branch.objects.create(name="Alausa Station", parent=d1, level=L.STATION)
    hq = Branch.objects.create(name="Yaba Central Station", parent=d2, level=L.STATION, is_national_headquarters=True)
    return hq, area, d1, d2, s1, s2


def test_valid_chain_passes_validation(chain):
    for b in chain:
        b.full_clean()


def test_station_cannot_skip_the_district(chain):
    hq, area, *_ = chain
    with pytest.raises(ValidationError) as e:
        Branch(name="Bad", level=L.STATION, parent=area).full_clean()
    assert "district" in str(e.value).lower()


def test_district_needs_an_area_parent(chain):
    hq, *_ = chain
    with pytest.raises(ValidationError):
        Branch(name="Bad", level=L.DISTRICT, parent=hq).full_clean()
    with pytest.raises(ValidationError):
        Branch(name="Orphan", level=L.DISTRICT).full_clean()


def test_area_stands_alone_and_hq_is_a_station(chain):
    hq, area, d1, *_ = chain
    area.parent = d1
    with pytest.raises(ValidationError):
        area.full_clean()
    assert hq.level == L.STATION and hq.is_national_headquarters and hq.level_note == "National Headquarters"
    area.parent = None
    d1.is_national_headquarters = True  # a district cannot be the headquarters
    with pytest.raises(ValidationError):
        d1.full_clean()


def test_counts_and_descendants(chain):
    hq, area, d1, *_ = chain
    assert area.counts() == {"districts": 2, "stations": 3}
    assert d1.counts() == {"stations": 2}
    assert area.child_label_plural == "Districts" and d1.child_label_plural == "Stations"


def test_structure_page_shows_nested_tree(client, chain):
    html = client.get(reverse("churches:list")).content.decode()
    for name in ("Lagos Area", "Ikeja District", "Allen Station"):
        assert name in html
    assert html.index("Lagos Area") < html.index("Ikeja District") < html.index("Allen Station")


def test_filter_by_level_and_search(client, chain):
    html = client.get(reverse("churches:list"), {"level": "district"}).content.decode()
    assert "Ikeja District" in html and "Allen Station" not in html
    html = client.get(reverse("churches:list"), {"q": "alausa"}).content.decode()
    assert "Alausa Station" in html and "Yaba District" not in html


def test_detail_lists_children_and_breadcrumbs(client, chain):
    hq, area, d1, *_ = chain
    html = client.get(d1.get_absolute_url()).content.decode()
    assert "Stations under Ikeja District" in html and "Allen Station" in html
    assert "Lagos Area" in html  # breadcrumb chain
    html = client.get(area.get_absolute_url()).content.decode()
    assert "Districts under Lagos Area" in html and "Ikeja District" in html


def _png(name="p.png"):
    buf = io.BytesIO()
    Image.new("RGB", (40, 40), (11, 42, 91)).save(buf, "PNG")
    return SimpleUploadedFile(name, buf.getvalue(), content_type="image/png")


def test_general_council_page_and_member_profile(client, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    c = Council.objects.create(name="General Council", description="Oversees the church.")
    assert c.slug == "general-council" and c.is_general
    m = CouncilMember.objects.create(council=c, name="Samuel Adeyemi", title="General Overseer",
                                     bio="Serving since the founding.", term_start=1984, photo=_png(),
                                     email="x@example.org", phone="0800", show_contact=False)
    CouncilMember.objects.create(council=c, name="Old Elder", title="Secretary", is_current=False, term_start=1990, term_end=2005)
    html = client.get(reverse("leadership:list")).content.decode()
    assert "General Council" in html and "Samuel Adeyemi" in html and "General Overseer" in html
    assert "Old Elder" not in html  # past holders only on the council page
    html = client.get(c.get_absolute_url()).content.decode()
    assert "Past office holders" in html and "Old Elder" in html
    html = client.get(m.get_absolute_url()).content.decode()
    assert "Serving since the founding." in html and "since 1984" in html
    assert "x@example.org" not in html and "0800" not in html  # contact hidden by default
    m.show_contact = True
    m.save()
    assert "x@example.org" in client.get(m.get_absolute_url()).content.decode()


def test_member_without_photo_gets_initials(client):
    c = Council.objects.create(name="Board")
    m = CouncilMember.objects.create(council=c, name="Grace Okafor", title="Chair")
    assert m.initials == "GO"
    assert "GO" in client.get(m.get_absolute_url()).content.decode()


def test_inactive_council_and_wrong_member_404(client):
    c = Council.objects.create(name="Hidden", is_active=False)
    m = CouncilMember.objects.create(council=c, name="X")
    assert client.get(c.get_absolute_url()).status_code == 404
    other = Council.objects.create(name="Other")
    assert client.get(reverse("leadership:member", args=[other.slug, m.pk])).status_code == 404


def test_oversized_photo_rejected(settings):
    settings.MAX_IMAGE_MB = 1
    big = SimpleUploadedFile("big.png", b"0" * (2 * 1024 * 1024), content_type="image/png")
    m = CouncilMember(council=Council.objects.create(name="C"), name="N", photo=big)
    with pytest.raises(ValidationError):
        m.full_clean()


def test_branch_council_shows_on_branch_page(client, chain):
    *_, d1, _d2, _s1, _s2 = chain
    c = Council.objects.create(name="District Council", branch=d1)
    CouncilMember.objects.create(council=c, name="Pastor Ade", title="District Pastor")
    html = client.get(d1.get_absolute_url()).content.decode()
    assert "District Council" in html and "Pastor Ade" in html
    assert not c.is_general


def test_private_ips_only_returns_lan_addresses(monkeypatch):
    from apps.core.management.commands import runlan

    monkeypatch.setattr(runlan, "_routed_ip", lambda: "192.168.1.20")
    monkeypatch.setattr(
        runlan.socket, "getaddrinfo",
        lambda *a, **k: [(2, 1, 6, "", (ip, 0)) for ip in ("127.0.0.1", "169.254.3.3", "8.8.8.8", "192.168.137.1", "192.168.1.20")],
    )
    assert runlan.private_ips() == ["192.168.1.20", "192.168.137.1"]
    assert "Mobile Hotspot" in runlan.describe("192.168.137.1")


# ---- one National Headquarters, superintendents, directory ------------------
from apps.churches.models import BranchLeader, Membership  # noqa: E402


def test_only_one_national_headquarters(chain):
    _, _, d1, *_ = chain
    with pytest.raises(ValidationError) as e:
        Branch(name="Second HQ", level=L.STATION, parent=d1, is_national_headquarters=True).full_clean()
    assert "already" in str(e.value).lower()
    from django.db import IntegrityError, transaction
    with pytest.raises(IntegrityError), transaction.atomic():
        Branch.objects.create(name="Third HQ", level=L.STATION, parent=d1, is_national_headquarters=True)


def test_superintendent_only_for_areas_and_districts(chain):
    hq, area, d1, d2, s1, s2 = chain
    BranchLeader(branch=area, name="A", role="superintendent").full_clean()
    BranchLeader(branch=d1, name="B", role="superintendent").full_clean()
    with pytest.raises(ValidationError):
        BranchLeader(branch=s1, name="C", role="superintendent").full_clean()
    BranchLeader(branch=s1, name="C", role="pastor").full_clean()


def test_one_serving_superintendent_per_unit(chain):
    _, area, *_ = chain
    BranchLeader.objects.create(branch=area, name="First", role="superintendent")
    with pytest.raises(ValidationError):
        BranchLeader(branch=area, name="Second", role="superintendent").full_clean()
    old = BranchLeader.objects.get(name="First")
    old.is_current = False
    old.save()
    BranchLeader(branch=area, name="Second", role="superintendent").full_clean()  # fine once the first has stepped down


def test_titles_and_head_lookup(chain):
    _, area, d1, *_ = chain
    a = BranchLeader.objects.create(branch=area, name="Rev. Ade", role="superintendent")
    d = BranchLeader.objects.create(branch=d1, name="Pst. Bola", role="superintendent")
    assert a.display_title == "Area Superintendent" and d.display_title == "District Superintendent"
    assert area.superintendent.name == "Rev. Ade"
    BranchLeader.objects.create(branch=d1, name="Custom", role="superintendent", title="Rt. Rev.", is_current=False)
    assert d1.superintendent.name == "Pst. Bola"


def test_linked_superintendent_can_manage_the_units_below(chain, django_user_model):
    from apps.core.permissions import can_manage_branch
    hq, area, d1, d2, s1, s2 = chain
    u = django_user_model.objects.create_user("supt", password="pw-12345678")
    assert not can_manage_branch(u, s1)
    BranchLeader.objects.create(branch=area, name="Supt", role="superintendent", user=u)
    assert Membership.objects.get(user=u, branch=area).role == "admin"
    assert can_manage_branch(u, s1) and can_manage_branch(u, d2)
    other = Branch.objects.create(name="Other Area", level=L.AREA)
    assert not can_manage_branch(u, other)


def test_directory_sorting_filtering_and_pagination(client, chain):
    hq, area, d1, d2, s1, s2 = chain
    BranchLeader.objects.create(branch=d1, name="Zed Supt", role="superintendent")
    url = reverse("churches:list")
    html = client.get(url, {"level": "local", "sort": "name"}).content.decode()
    assert html.index("Alausa Station") < html.index("Allen Station")
    html = client.get(url, {"level": "local", "sort": "-name"}).content.decode()
    assert html.index("Allen Station") < html.index("Alausa Station")
    # filter by district: only its stations, and the area/district columns are filled in
    r = client.get(url, {"district": d1.slug, "level": "local"})
    assert sorted(b.name for b in r.context["page"].object_list) == ["Alausa Station", "Allen Station"]
    assert r.context["page"].object_list[0].area_unit.name == "Lagos Area"
    # search by superintendent name
    r = client.get(url, {"q": "zed"})
    assert [b.name for b in r.context["page"].object_list] == ["Ikeja District"]
    # junk sort values fall back safely
    assert client.get(url, {"sort": "'; drop table"}).status_code == 200
    # pagination
    for i in range(25):
        Branch.objects.create(name=f"Extra {i:02d}", level=L.STATION, parent=d2)
    r = client.get(url, {"level": "local"})
    assert r.context["page"].paginator.num_pages == 2 and r.context["count"] == 28


def test_tree_shows_superintendent_and_detail_shows_leaders(client, chain):
    hq, area, d1, *_ = chain
    BranchLeader.objects.create(branch=d1, name="Pst. Bola Ade", role="superintendent")
    assert "Pst. Bola Ade" in client.get(reverse("churches:list")).content.decode()
    html = client.get(d1.get_absolute_url()).content.decode()
    assert "District Superintendent" in html and "Pst. Bola Ade" in html


def test_contact_details_hidden_by_default(client, chain):
    _, area, *_ = chain
    BranchLeader.objects.create(branch=area, name="Rev", role="superintendent", phone="0801234", email="rev@example.org")
    assert "0801234" not in client.get(area.get_absolute_url()).content.decode()


def test_home_shows_stats_and_leadership(client, chain):
    c = Council.objects.create(name="General Council")
    CouncilMember.objects.create(council=c, name="Samuel Adeyemi", title="General Overseer")
    html = client.get(reverse("core:home")).content.decode()
    assert 'data-count="1"' in html and "Local churches" in html
    assert "Samuel Adeyemi" in html and "How the church is organised" in html


def test_password_fields_are_on_login_and_signup(client):
    for name in ("accounts:login", "accounts:signup"):
        html = client.get(reverse(name)).content.decode()
        assert 'type="password"' in html
        assert "js/app.js" in html  # the script that adds the show/hide button


# ---- separate Areas / Districts / Stations pages, HQ, pictures ----------------------------
def test_areas_districts_and_stations_have_their_own_pages(client, chain):
    hq, area, d1, d2, s1, s2 = chain
    html = client.get(reverse("churches:areas")).content.decode()
    assert "Lagos Area" in html and "2 districts" in html and "Ikeja District" not in html
    html = client.get(reverse("churches:districts")).content.decode()
    assert "Ikeja District" in html and "Yaba District" in html and "Allen Station" not in html
    r = client.get(reverse("churches:districts"), {"area": area.slug})
    assert r.context["count"] == 2
    html = client.get(reverse("churches:stations")).content.decode()
    assert "Allen Station" in html and "Yaba Central Station" in html and "National Headquarters" in html
    r = client.get(reverse("churches:stations"), {"district": d1.slug})
    assert sorted(b.name for b in r.context["page"].object_list) == ["Alausa Station", "Allen Station"]


def test_headquarters_link_goes_to_the_hq_station(client, chain):
    hq, *_ = chain
    r = client.get(reverse("churches:headquarters"))
    assert r.status_code == 302 and r["Location"] == hq.get_absolute_url()
    assert "National Headquarters" in client.get(hq.get_absolute_url()).content.decode()


def test_legacy_headquarters_unit_is_converted(chain):
    from apps.churches.structure import convert_legacy_headquarters
    hq, area, *_ = chain
    old = Branch(name="National Headquarters", level="hq")
    old.save()
    Branch.objects.filter(pk=area.pk).update(parent=old)
    assert convert_legacy_headquarters(out=lambda *_: None) == 1
    area.refresh_from_db()
    assert area.parent_id is None and not Branch.objects.filter(level="hq").exists()


def test_leader_photo_shows_on_unit_page_and_list(client, chain, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    _, area, d1, *_ = chain
    BranchLeader.objects.create(branch=d1, name="Pst. Bola", role="superintendent", photo=_png("bola.png"))
    for url in (d1.get_absolute_url(), reverse("churches:districts"), reverse("churches:list") + "?view=table"):
        html = client.get(url).content.decode()
        assert "branches/leaders/bola" in html, url
    media = client.get(BranchLeader.objects.get(name="Pst. Bola").photo.url)
    assert media.status_code == 200  # uploads are actually served


def test_missing_file_falls_back_to_initials_not_a_broken_image(client, chain, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    _, area, d1, *_ = chain
    BranchLeader.objects.create(branch=d1, name="Pst. Bola", role="superintendent", photo="branches/leaders/gone.png")
    html = client.get(d1.get_absolute_url()).content.decode()
    assert "gone.png" not in html and "PB" in html


def test_branch_logo_and_cover_show_on_the_unit_page(client, chain, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    _, area, *_ = chain
    area.logo, area.cover = _png("logo.png"), _png("cover.png")
    area.save()
    html = client.get(area.get_absolute_url()).content.decode()
    assert "branches/logos/logo" in html and "branches/covers/cover" in html


def test_council_group_picture_shows_on_the_leadership_page(client, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    Council.objects.create(name="General Council", cover=_png("gc.png"))
    assert "councils/covers/gc" in client.get(reverse("leadership:list")).content.decode()


def test_big_phone_photo_is_shrunk_not_refused(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    from apps.core.images import MAX_SIDE
    buf = io.BytesIO()
    Image.new("RGB", (4000, 3000), (10, 60, 120)).save(buf, "JPEG", quality=95)
    up = SimpleUploadedFile("phone.jpg", buf.getvalue(), content_type="image/jpeg")
    m = CouncilMember.objects.create(council=Council.objects.create(name="C"), name="N", photo=up)
    m.refresh_from_db()
    with Image.open(m.photo.path) as saved:
        assert max(saved.size) == MAX_SIDE
    assert m.photo.storage.exists(m.photo.name)


def test_only_the_registered_structure_remains(chain):
    from apps.churches.structure import remove_demo_units
    demo = Branch.objects.create(name="Central Area", slug="central-area", level=L.AREA)
    Branch.objects.create(name="Central District", slug="central-district", level=L.DISTRICT, parent=demo)
    assert remove_demo_units(out=lambda *_: None) == 2
    assert not Branch.objects.filter(slug__startswith="central-").exists()
    assert Branch.objects.filter(name="Lagos Area").exists()
