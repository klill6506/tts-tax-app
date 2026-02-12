import pytest
from django.test import Client


@pytest.mark.django_db
def test_health_endpoint_returns_ok():
    client = Client()
    response = client.get("/api/v1/health/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_endpoint_allows_unauthenticated():
    """Health check must not require auth."""
    client = Client()
    response = client.get("/api/v1/health/")
    assert response.status_code == 200
