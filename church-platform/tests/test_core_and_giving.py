import json

import pytest

from apps.giving.models import Donation, Fund

pytestmark = pytest.mark.django_db


def test_home_renders(client):
    assert client.get("/").status_code == 200


def test_manifest_is_valid_json(client):
    resp = client.get("/manifest.webmanifest")
    assert resp.status_code == 200
    data = resp.json()
    assert data["display"] == "standalone"
    assert {i["sizes"] for i in data["icons"]} >= {"192x192", "512x512"}


def test_service_worker_scope_header(client):
    resp = client.get("/service-worker.js")
    assert resp.status_code == 200
    assert resp["Service-Worker-Allowed"] == "/"
    assert "javascript" in resp["Content-Type"]


def test_signup_and_login_pages(client):
    assert client.get("/accounts/signup/").status_code == 200
    assert client.get("/accounts/login/").status_code == 200


def test_api_signup(client):
    resp = client.post(
        "/api/auth/signup",
        data={"username": "new", "email": "new@example.org", "password": "a-long-password"},
        content_type="application/json",
    )
    assert resp.status_code == 201
    assert client.get("/api/auth/me").json()["username"] == "new"


def test_dummy_donation_flow(client, settings, monkeypatch):
    monkeypatch.setattr("apps.giving.api.send_donation_receipt.delay", lambda *a, **k: None)
    settings.DEBUG = True
    settings.PAYMENT_PROVIDER = "dummy"
    Fund.objects.create(name="General", slug="general")

    resp = client.post(
        "/api/giving/donations",
        data={"fund_slug": "general", "amount": "25.00", "donor_email": "d@example.org"},
        content_type="application/json",
    )
    assert resp.status_code == 201
    ref = resp.json()["reference"]
    assert Donation.objects.get(reference=ref).status == Donation.Status.PENDING

    hook = client.post(
        "/api/giving/webhooks/dummy",
        data=json.dumps({"reference": ref, "status": "succeeded"}),
        content_type="application/json",
    )
    assert hook.status_code == 200
    assert Donation.objects.get(reference=ref).status == Donation.Status.SUCCEEDED


def test_negative_amount_rejected(client):
    Fund.objects.create(name="General", slug="general")
    resp = client.post(
        "/api/giving/donations",
        data={"fund_slug": "general", "amount": "-5"},
        content_type="application/json",
    )
    assert resp.status_code == 422
