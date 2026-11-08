import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse

pytestmark = pytest.mark.django_db


def test_security_headers_and_nonce(client):
    r = client.get(reverse("core:home"))
    csp = r["Content-Security-Policy"]
    assert "frame-ancestors 'none'" in csp and "object-src 'none'" in csp
    nonce = r.wsgi_request.csp_nonce
    assert f"'nonce-{nonce}'" in csp
    assert f'nonce="{nonce}"' in r.content.decode()  # the inline theme script carries it
    assert r["X-Content-Type-Options"] == "nosniff"
    assert r["Referrer-Policy"]
    assert "camera=()" in r["Permissions-Policy"]
    assert r["X-Frame-Options"] == "DENY"


@override_settings(RATE_LIMIT_PER_MIN=5)
def test_general_rate_limit(client):
    codes = [client.get(reverse("core:home")).status_code for _ in range(8)]
    assert codes[:5] == [200] * 5
    assert 429 in codes[5:]
    assert client.get(reverse("core:home")).get("Retry-After") == "60"


@override_settings(LOGIN_MAX_FAILURES=3, RATE_LIMIT_SENSITIVE_PER_MIN=100)
def test_login_lockout_after_repeated_failures(client):
    get_user_model().objects.create_user(username="grace", password="correct-horse-9")
    url = reverse("accounts:login")
    for _ in range(3):
        assert client.post(url, {"username": "grace", "password": "nope"}).status_code == 200
    # Even the right password is refused while locked out.
    r = client.post(url, {"username": "grace", "password": "correct-horse-9"})
    assert r.status_code == 429


@override_settings(RATE_LIMIT_SENSITIVE_PER_MIN=3)
def test_sensitive_posts_are_throttled(client):
    url = reverse("accounts:login")
    codes = [client.post(url, {"username": "x", "password": "y"}).status_code for _ in range(5)]
    assert codes[-1] == 429


def test_static_files_are_not_counted(client):
    with override_settings(RATE_LIMIT_PER_MIN=2):
        for _ in range(6):
            client.get("/service-worker.js")
        assert client.get(reverse("core:home")).status_code == 200


def test_forwarded_header_ignored_unless_trusted(client):
    from apps.core.security import client_ip
    from django.test import RequestFactory
    req = RequestFactory().get("/", HTTP_X_FORWARDED_FOR="9.9.9.9", REMOTE_ADDR="1.2.3.4")
    assert client_ip(req) == "1.2.3.4"
    with override_settings(TRUST_PROXY_HEADERS=True):
        assert client_ip(req) == "9.9.9.9"


def test_ensure_admin_creates_and_resets(monkeypatch, django_user_model):
    from django.core.management import call_command
    monkeypatch.setenv("DJANGO_SUPERUSER_USERNAME", "boss")
    monkeypatch.setenv("DJANGO_SUPERUSER_EMAIL", "boss@example.org")
    monkeypatch.setenv("DJANGO_SUPERUSER_PASSWORD", "first-pass-123")
    call_command("ensure_admin")
    u = django_user_model.objects.get(username="boss")
    assert u.is_superuser and u.check_password("first-pass-123")
    monkeypatch.setenv("DJANGO_SUPERUSER_PASSWORD", "second-pass-456")
    call_command("ensure_admin")
    u.refresh_from_db()
    assert u.check_password("first-pass-123")  # not changed without the reset flag
    monkeypatch.setenv("ADMIN_RESET_PASSWORD", "1")
    call_command("ensure_admin")
    u.refresh_from_db()
    assert u.check_password("second-pass-456")
