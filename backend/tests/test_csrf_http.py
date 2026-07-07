import os

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["APP_ENV"] = "test"

from fastapi.testclient import TestClient

from app import auth
from app.main import app


def test_cookie_authenticated_unsafe_request_requires_csrf():
    client = TestClient(app)
    client.cookies.set("access_token", auth.create_access_token({"sub": "user@example.com"}))

    response = client.post("/api/auth/logout", json={})

    assert response.status_code == 403
    assert response.json()["detail"] == "Missing CSRF token"


def test_cookie_authenticated_unsafe_request_accepts_matching_csrf():
    client = TestClient(app)
    csrf_token = "test-csrf-token"
    client.cookies.set("access_token", auth.create_access_token({"sub": "user@example.com"}))
    client.cookies.set(auth.CSRF_COOKIE_NAME, csrf_token)

    response = client.post(
        "/api/auth/logout",
        headers={"X-CSRF-Token": csrf_token},
        json={},
    )

    assert response.status_code == 200
