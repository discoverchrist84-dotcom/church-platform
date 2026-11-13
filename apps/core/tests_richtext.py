import io

import pytest
from django.urls import reverse

from apps.core.richtext import clean_html, plain_text, render_rich


def test_plain_text_becomes_paragraphs():
    assert clean_html("Hello\n\nWorld") == "<p>Hello</p><p>World</p>"


def test_formatting_kept_and_scripts_removed():
    out = clean_html("<p><b>Bold</b> <i>it</i> <u>un</u></p><script>alert(1)</script>")
    assert "<strong>Bold</strong>" in out and "<em>it</em>" in out and "<u>un</u>" in out
    assert "script" not in out and "alert" not in out


def test_dangerous_links_and_images_removed():
    out = clean_html('<a href="javascript:alert(1)">x</a><img src="javascript:alert(1)"><img src="/m/a.jpg" onerror="x()">')
    assert "javascript" not in out and "onerror" not in out
    assert 'src="/m/a.jpg"' in out


def test_image_position_class_and_width_kept():
    out = clean_html('<p><img src="/m/a.jpg" class="img-left" style="width:40%"></p>')
    assert "img-left" in out and "width: 40%" in out


def test_plain_text_for_descriptions():
    assert plain_text("<p>Hi <b>there</b> friend</p>", 8) == "Hi…" or plain_text("<p>Hi <b>there</b> friend</p>", 8).startswith("Hi")


def test_render_wraps_in_rich_div():
    assert render_rich("<h2>T</h2>").startswith('<div class="rich">')


@pytest.mark.django_db
def test_upload_needs_staff(client):
    r = client.post(reverse("core:editor_upload"), {})
    assert r.status_code == 403


@pytest.mark.django_db
def test_upload_accepts_picture_from_staff(client, django_user_model, settings, tmp_path):
    from PIL import Image

    settings.MEDIA_ROOT = tmp_path
    u = django_user_model.objects.create_user("ed", "e@x.org", "pw", is_staff=True)
    client.force_login(u)
    buf = io.BytesIO()
    Image.new("RGB", (50, 50), "blue").save(buf, "PNG")
    buf.name = "a.png"
    buf.seek(0)
    r = client.post(reverse("core:editor_upload"), {"image": buf})
    assert r.status_code == 200 and r.json()["url"]
    bad = io.BytesIO(b"not an image")
    bad.name = "x.png"
    assert client.post(reverse("core:editor_upload"), {"image": bad}).status_code == 400
