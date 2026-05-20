"""T-3-010: тесты auth endpoints."""
import pytest
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


@pytest.fixture
def client():
    return APIClient()


def test_login_valid_credentials(client, db):
    from tests.factories import MsUserFactory
    user = MsUserFactory(username="testlogin")
    user.set_password("correct_password")
    user.save()
    response = client.post("/api/v1/auth/login/",
                           {"username": "testlogin", "password": "correct_password"},
                           format="json")
    assert response.status_code == 200
    assert "access" in response.data
    assert "mstech_refresh" in response.cookies


def test_login_wrong_password_returns_401(client, db):
    from tests.factories import MsUserFactory
    user = MsUserFactory(username="wrongpwd")
    user.set_password("correct")
    user.save()
    response = client.post("/api/v1/auth/login/",
                           {"username": "wrongpwd", "password": "wrong"},
                           format="json")
    assert response.status_code == 401
    assert response.data["code"] == "invalid_credentials"


def test_login_empty_body_returns_422(client):
    response = client.post("/api/v1/auth/login/", {}, format="json")
    assert response.status_code == 422
    assert response.data["code"] == "validation_error"


def test_me_returns_current_user(db):
    from tests.factories import MsUserFactory
    user = MsUserFactory(username="metest", permission="control")
    c = APIClient()
    c.force_authenticate(user=user)
    response = c.get("/api/v1/me")
    assert response.status_code == 200
    assert response.data["username"] == "metest"
    assert response.data["permission"] == "control"


def test_me_patch_telegram_id(db):
    from tests.factories import MsUserFactory
    user = MsUserFactory()
    c = APIClient()
    c.force_authenticate(user=user)
    response = c.patch("/api/v1/me", {"telegram_id": "98765"}, format="json")
    assert response.status_code == 200
    assert response.data["telegram_id"] == "98765"


def test_health_live_no_auth(client):
    response = client.get("/api/v1/health/live")
    assert response.status_code == 200
    assert response.data["status"] == "alive"


def test_metrics_endpoint_no_auth(client):
    response = client.get("/metrics")

    assert response.status_code == 200
    assert "text/plain" in response["Content-Type"]
    assert "django_http" in response.content.decode("utf-8")
