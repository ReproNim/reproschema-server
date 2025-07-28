"""
Pytest configuration for ReproSchema Server tests
"""
import sys
import os
from pathlib import Path
import tempfile

# Add the backend directory to Python path
backend_dir = Path(__file__).parent.parent / "docker" / "backend"
sys.path.insert(0, str(backend_dir))

# Set default test environment variables
os.environ.setdefault('ENV', 'test')
os.environ.setdefault('JWT_SECRET_KEY', 'test-secret-key-for-testing-only')
os.environ.setdefault('INITIAL_TOKEN', 'test-initial-token')
os.environ.setdefault('DEV_MODE', '1')

# Create a temporary directory for tests
test_dir = tempfile.mkdtemp(prefix='reproschema-test-')
os.environ.setdefault('REPROSCHEMA_BACKEND_BASEDIR', test_dir)

# Create required directories
Path(test_dir).joinpath('schemas').mkdir(exist_ok=True, parents=True)
Path(test_dir).joinpath('responses').mkdir(exist_ok=True, parents=True)