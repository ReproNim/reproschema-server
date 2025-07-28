"""
Comprehensive test suite for ReproSchema Server API
Tests security, validation, error handling, and core functionality
"""
import pytest
import json
import jwt
import bcrypt
import tempfile
import os
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

# Import the app and related modules
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'docker', 'backend'))

from app import app
from auth import AuthManager
from validation import DataValidator, ValidationError

@pytest.fixture
def test_app():
    """Create test app instance"""
    # Set test environment variables
    os.environ['ENV'] = 'test'
    os.environ['JWT_SECRET_KEY'] = 'test-secret-key-for-testing-only'
    os.environ['INITIAL_TOKEN'] = 'test-initial-token'
    os.environ['DEV_MODE'] = '1'
    
    # Create test data directory
    with tempfile.TemporaryDirectory() as tmpdir:
        os.environ['REPROSCHEMA_BACKEND_BASEDIR'] = tmpdir
        yield app

@pytest.fixture
def auth_manager():
    """Create auth manager for testing"""
    return AuthManager()

@pytest.fixture
def valid_token(auth_manager):
    """Generate a valid JWT token for testing"""
    token, expires = auth_manager.create_auth_token(
        user_id='test_user',
        project='test_project',
        expiry_minutes=60
    )
    return token

# Test Authentication
class TestAuthentication:
    @pytest.mark.asyncio
    async def test_get_token_success(self, test_app):
        """Test successful token generation"""
        request, response = await test_app.asgi_client.get(
            '/api/token?token=test-initial-token&project=test_project'
        )
        assert response.status == 200
        data = response.json
        assert 'auth_token' in data
        assert 'expires' in data
        assert data['project'] == 'test_project'
        
    @pytest.mark.asyncio
    async def test_get_token_invalid_initial_token(self, test_app):
        """Test token generation with invalid initial token"""
        request, response = await test_app.asgi_client.get(
            '/api/token?token=invalid-token&project=test_project'
        )
        assert response.status == 400
        assert 'error' in response.json
        
    @pytest.mark.asyncio
    async def test_get_token_missing_params(self, test_app):
        """Test token generation with missing parameters"""
        request, response = await test_app.asgi_client.get('/api/token')
        assert response.status == 400
        assert 'Token parameter is required' in response.json['error']
        
    @pytest.mark.asyncio
    async def test_refresh_token_success(self, test_app, valid_token):
        """Test successful token refresh"""
        request, response = await test_app.asgi_client.post(
            '/api/token/refresh',
            headers={'Authorization': f'Bearer {valid_token}'},
            json={'expiry_minutes': 120}
        )
        assert response.status == 200
        assert 'auth_token' in response.json
        
    @pytest.mark.asyncio
    async def test_refresh_token_expired(self, test_app, auth_manager):
        """Test token refresh with expired token"""
        # Create an expired token
        expired_token = jwt.encode(
            {
                'user_id': 'test_user',
                'project': 'test_project',
                'exp': datetime.utcnow() - timedelta(hours=1)
            },
            auth_manager.secret_key,
            algorithm=auth_manager.algorithm
        )
        
        request, response = await test_app.asgi_client.post(
            '/api/token/refresh',
            headers={'Authorization': f'Bearer {expired_token}'}
        )
        assert response.status == 401

# Test Input Validation
class TestValidation:
    def test_validate_project_name(self):
        """Test project name validation"""
        # Valid names
        assert DataValidator.validate_project_name('test-project') == 'test-project'
        assert DataValidator.validate_project_name('test_project_123') == 'test_project_123'
        
        # Invalid names
        with pytest.raises(ValidationError):
            DataValidator.validate_project_name('')
        with pytest.raises(ValidationError):
            DataValidator.validate_project_name('test project')  # Space not allowed
        with pytest.raises(ValidationError):
            DataValidator.validate_project_name('a' * 51)  # Too long
            
    def test_validate_user_id(self):
        """Test user ID validation"""
        # Valid IDs
        assert DataValidator.validate_user_id('user.123') == 'user.123'
        assert DataValidator.validate_user_id('test_user-456') == 'test_user-456'
        
        # Invalid IDs
        with pytest.raises(ValidationError):
            DataValidator.validate_user_id('')
        with pytest.raises(ValidationError):
            DataValidator.validate_user_id('user@test')  # @ not allowed
            
    def test_validate_schema_url(self):
        """Test schema URL validation"""
        # Valid URLs
        valid_url = 'https://example.com/schema.json'
        assert DataValidator.validate_schema_url(valid_url) == valid_url
        
        # Invalid URLs
        with pytest.raises(ValidationError):
            DataValidator.validate_schema_url('javascript:alert(1)')
        with pytest.raises(ValidationError):
            DataValidator.validate_schema_url('ftp://example.com')  # Only HTTP/HTTPS
        with pytest.raises(ValidationError):
            DataValidator.validate_schema_url('not-a-url')
            
    def test_sanitize_filename(self):
        """Test filename sanitization"""
        # Safe filenames
        assert DataValidator.sanitize_filename('test.json') == 'test.json'
        
        # Dangerous filenames
        assert DataValidator.sanitize_filename('../../../etc/passwd') == 'passwd'
        assert DataValidator.sanitize_filename('test<script>.json') == 'test_script_.json'
        assert DataValidator.sanitize_filename('con.txt') == 'con.txt'  # Windows reserved
        
    def test_validate_response_data(self):
        """Test response data validation"""
        # Valid data
        valid_data = {
            'name': 'test',
            'values': [1, 2, 3],
            'nested': {'key': 'value'}
        }
        assert DataValidator.validate_response_data(valid_data) == valid_data
        
        # XSS attempt
        with pytest.raises(ValidationError):
            DataValidator.validate_response_data({'xss': '<script>alert(1)</script>'})
            
        # Too deep nesting
        deeply_nested = {'level': 0}
        current = deeply_nested
        for i in range(15):
            current['next'] = {'level': i + 1}
            current = current['next']
        
        with pytest.raises(ValidationError):
            DataValidator.validate_response_data(deeply_nested)

# Test API Endpoints
class TestAPIEndpoints:
    @pytest.mark.asyncio
    async def test_health_check(self, test_app):
        """Test health check endpoint"""
        request, response = await test_app.asgi_client.get('/api/health')
        assert response.status == 200
        data = response.json
        assert data['status'] in ['healthy', 'degraded']
        assert 'timestamp' in data
        assert 'services' in data
        
    @pytest.mark.asyncio
    async def test_submit_response_success(self, test_app, valid_token):
        """Test successful response submission"""
        test_data = {
            'assessment': 'test',
            'responses': [
                {'item': 'q1', 'value': 'answer1'},
                {'item': 'q2', 'value': 'answer2'}
            ]
        }
        
        request, response = await test_app.asgi_client.post(
            '/api/responses',
            headers={
                'Authorization': f'Bearer {valid_token}',
                'Content-Type': 'application/json'
            },
            json=test_data
        )
        assert response.status == 200
        assert response.json['status'] == 'success'
        assert 'response_id' in response.json
        
    @pytest.mark.asyncio
    async def test_submit_response_invalid_data(self, test_app, valid_token):
        """Test response submission with invalid data"""
        invalid_data = {
            'xss_attempt': '<script>alert("xss")</script>'
        }
        
        request, response = await test_app.asgi_client.post(
            '/api/responses',
            headers={
                'Authorization': f'Bearer {valid_token}',
                'Content-Type': 'application/json'
            },
            json=invalid_data
        )
        assert response.status == 400
        assert 'error' in response.json
        
    @pytest.mark.asyncio
    async def test_submit_response_no_auth(self, test_app):
        """Test response submission without authentication"""
        request, response = await test_app.asgi_client.post(
            '/api/responses',
            json={'test': 'data'}
        )
        assert response.status == 401
        
    @pytest.mark.asyncio
    async def test_get_schema_local(self, test_app, valid_token):
        """Test getting schema from local file"""
        # Create a test schema file
        test_schema = {'test': 'schema', 'version': '1.0.0'}
        schema_dir = Path(os.environ['REPROSCHEMA_BACKEND_BASEDIR']) / 'schemas'
        schema_dir.mkdir(exist_ok=True)
        schema_file = schema_dir / 'test_schema.json'
        
        with open(schema_file, 'w') as f:
            json.dump(test_schema, f)
        
        request, response = await test_app.asgi_client.get(
            '/api/schema/test_schema.json',
            headers={'Authorization': f'Bearer {valid_token}'}
        )
        assert response.status == 200
        assert response.json == test_schema
        
    @pytest.mark.asyncio
    async def test_get_schema_path_traversal(self, test_app, valid_token):
        """Test schema endpoint against path traversal"""
        request, response = await test_app.asgi_client.get(
            '/api/schema/../../../etc/passwd',
            headers={'Authorization': f'Bearer {valid_token}'}
        )
        assert response.status == 400
        
    @pytest.mark.asyncio
    async def test_register_dev_mode(self, test_app):
        """Test registration endpoint in dev mode"""
        request, response = await test_app.asgi_client.get(
            '/api/register?token=test-initial-token&callback_url=https://example.com/callback'
        )
        assert response.status == 200
        assert response.json['status'] == 'registered'

# Test Security Features
class TestSecurity:
    def test_jwt_secret_required_in_production(self):
        """Test that JWT secret is required in production"""
        # Temporarily modify environment
        original_env = os.environ.get('ENV')
        original_key = os.environ.get('JWT_SECRET_KEY')
        
        try:
            os.environ['ENV'] = 'production'
            if 'JWT_SECRET_KEY' in os.environ:
                del os.environ['JWT_SECRET_KEY']
                
            with pytest.raises(ValueError, match="JWT_SECRET_KEY must be set"):
                AuthManager()
        finally:
            # Restore environment
            if original_env:
                os.environ['ENV'] = original_env
            if original_key:
                os.environ['JWT_SECRET_KEY'] = original_key
                
    def test_initial_token_hashing(self, auth_manager):
        """Test that initial tokens are properly hashed"""
        # Verify token is hashed
        assert auth_manager.verify_initial_token('test-initial-token')
        assert not auth_manager.verify_initial_token('wrong-token')
        
    def test_sensitive_data_not_logged(self):
        """Test that sensitive data is filtered from logs"""
        from logging_config import SecurityFilter
        import logging
        
        # Create a log record with sensitive data
        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='test.py',
            lineno=1,
            msg='User token is secret123',
            args=(),
            exc_info=None
        )
        
        filter = SecurityFilter()
        filter.filter(record)
        
        assert 'secret123' not in record.getMessage()
        assert 'REDACTED' in record.getMessage()

# Test Error Handling
class TestErrorHandling:
    @pytest.mark.asyncio
    async def test_validation_error_handler(self, test_app):
        """Test validation error handling"""
        request, response = await test_app.asgi_client.get(
            '/api/token?token=test&project=invalid project name'
        )
        assert response.status == 400
        assert 'error' in response.json
        
    @pytest.mark.asyncio
    async def test_generic_error_handler(self, test_app):
        """Test generic error handling"""
        # Force an error by providing invalid JSON
        request, response = await test_app.asgi_client.post(
            '/api/responses',
            headers={'Content-Type': 'application/json'},
            data='invalid json'
        )
        assert response.status in [400, 500]
        assert 'error' in response.json

# Test Rate Limiting (placeholder for future implementation)
class TestRateLimiting:
    @pytest.mark.skip(reason="Rate limiting not yet implemented")
    @pytest.mark.asyncio
    async def test_rate_limit_token_endpoint(self, test_app):
        """Test rate limiting on token endpoint"""
        # Make multiple requests rapidly
        for i in range(10):
            request, response = await test_app.asgi_client.get(
                '/api/token?token=test-initial-token&project=test'
            )
        
        # Should get rate limited
        request, response = await test_app.asgi_client.get(
            '/api/token?token=test-initial-token&project=test'
        )
        assert response.status == 429  # Too Many Requests

if __name__ == '__main__':
    pytest.main([__file__, '-v'])