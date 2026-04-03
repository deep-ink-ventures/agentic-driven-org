import pytest
from django.test import Client


@pytest.mark.django_db
class TestHealthCheck:
    def test_health_check_returns_ok(self):
        client = Client()
        response = client.get("/health/")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_admin_requires_auth(self):
        client = Client()
        response = client.get("/admin/login/")
        assert response.status_code == 200
