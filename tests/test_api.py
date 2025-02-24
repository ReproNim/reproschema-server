import pytest
from app import app

@pytest.fixture
def test_app():
    return app

@pytest.mark.asyncio
async def test_health_endpoint(test_app):
    request, response = await test_app.asgi_client.get("/api/health")
    assert response.status == 200
    assert response.json["status"] == "healthy"

@pytest.mark.asyncio
async def test_root_endpoint(test_app):
    request, response = await test_app.asgi_client.get("/")
    assert response.status == 200
    assert response.json["status"] == "running"
    assert set(response.json["endpoints"]) == {
        "/api/health",
        "/api/token",
        "/api/responses",
        "/api/schema/<url>"
    } 