import pytest
import os
import tempfile
from pathlib import Path
from sanic import Sanic

@pytest.fixture
def test_app():
    # First clear any existing app instance
    Sanic.test_mode = True
    if "reproschema_backend" in Sanic._app_registry:
        del Sanic._app_registry["reproschema_backend"]
    
    # Set test environment variables
    old_env = os.environ.copy()
    os.environ['ENV'] = 'test'
    os.environ['JWT_SECRET_KEY'] = 'test-secret-key-for-testing-only'
    os.environ['INITIAL_TOKEN'] = 'test-initial-token'
    os.environ['DEV_MODE'] = '1'
    
    # Create test data directory
    with tempfile.TemporaryDirectory() as tmpdir:
        os.environ['REPROSCHEMA_BACKEND_BASEDIR'] = tmpdir
        # Create required directories
        Path(tmpdir).joinpath('schemas').mkdir(exist_ok=True)
        Path(tmpdir).joinpath('responses').mkdir(exist_ok=True)
        
        # Import app after setting env vars
        from app import app
        
        yield app
        
        # Cleanup
        if "reproschema_backend" in Sanic._app_registry:
            del Sanic._app_registry["reproschema_backend"]
        # Restore old env
        os.environ.clear()
        os.environ.update(old_env)

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
    assert response.json["name"] == "ReproSchema Server"
    # Check that endpoints is a dict with the expected keys
    endpoints = response.json["endpoints"]
    assert isinstance(endpoints, dict)
    expected_keys = {"health", "authentication", "refresh", "responses", "schema", "register"}
    assert set(endpoints.keys()) == expected_keys 