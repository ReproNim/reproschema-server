"""
Pytest configuration for ReproSchema Server tests
"""
import sys
import os
from pathlib import Path
import tempfile
import pytest
import shutil

# Add the backend directory to Python path
backend_dir = Path(__file__).parent.parent / "docker" / "backend"
sys.path.insert(0, str(backend_dir))

# DON'T set environment variables here - let the fixtures handle it
# This prevents module import issues

def pytest_configure(config):
    """Set up test configuration"""
    # Clear any cached modules that might have been imported
    modules_to_clear = ['config', 'app', 'auth', 'validation', 'logging_config']
    for module in modules_to_clear:
        if module in sys.modules:
            del sys.modules[module]

@pytest.fixture(scope='session')
def test_base_dir():
    """Create a base directory for all tests"""
    test_dir = tempfile.mkdtemp(prefix='reproschema-test-')
    yield test_dir
    # Cleanup after all tests
    shutil.rmtree(test_dir, ignore_errors=True)