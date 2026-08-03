import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.routes import public_enquiries
from app.security import BoundedInMemoryRateLimiter


VALID_ENQUIRY = {
    "name": "Amina Patel",
    "school": "Riverside Demonstration School",
    "role": "Deputy principal",
    "region": "Oman",
    "email": "amina@example.com",
    "message": "We would like to make family communication easier for teachers.",
}


@pytest.fixture
def client():
    with TestClient(create_app(), client=("127.0.0.1", 50000)) as test_client:
        yield test_client


def test_pilot_enquiry_validates_and_sends(client, monkeypatch):
    sent = []
    monkeypatch.setattr(public_enquiries, "send_pilot_enquiry", sent.append)
    monkeypatch.setattr(
        public_enquiries,
        "PILOT_ENQUIRY_RATE_LIMITER",
        BoundedInMemoryRateLimiter(600, 5),
    )

    response = client.post("/api/public/pilot-enquiries", json=VALID_ENQUIRY)

    assert response.status_code == 200
    assert response.json() == {"status": "sent"}
    assert len(sent) == 1
    assert sent[0].school == VALID_ENQUIRY["school"]
    assert sent[0].reply_to == VALID_ENQUIRY["email"]


def test_pilot_enquiry_rejects_invalid_fields(client, monkeypatch):
    send = lambda _enquiry: None
    monkeypatch.setattr(public_enquiries, "send_pilot_enquiry", send)

    invalid = {
        **VALID_ENQUIRY,
        "name": "Injected\nName",
        "email": "not-an-email",
        "message": "short",
    }
    response = client.post("/api/public/pilot-enquiries", json=invalid)

    assert response.status_code == 422


def test_pilot_enquiry_does_not_claim_success_when_mail_fails(client, monkeypatch):
    monkeypatch.setattr(
        public_enquiries,
        "PILOT_ENQUIRY_RATE_LIMITER",
        BoundedInMemoryRateLimiter(600, 5),
    )

    def fail_delivery(_enquiry):
        raise RuntimeError("smtp unavailable")

    monkeypatch.setattr(public_enquiries, "send_pilot_enquiry", fail_delivery)

    response = client.post("/api/public/pilot-enquiries", json=VALID_ENQUIRY)

    assert response.status_code == 503
    assert response.json()["detail"] == "Pilot enquiry email delivery is temporarily unavailable."


def test_pilot_enquiry_is_rate_limited_by_client_ip(client, monkeypatch):
    monkeypatch.setattr(public_enquiries, "send_pilot_enquiry", lambda _enquiry: None)
    monkeypatch.setattr(
        public_enquiries,
        "PILOT_ENQUIRY_RATE_LIMITER",
        BoundedInMemoryRateLimiter(600, 1),
    )

    first = client.post("/api/public/pilot-enquiries", json=VALID_ENQUIRY)
    second = client.post("/api/public/pilot-enquiries", json=VALID_ENQUIRY)

    assert first.status_code == 200
    assert second.status_code == 429
