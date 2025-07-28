"""
Unit tests for authentication module
"""
import pytest
import os
import jwt
from datetime import datetime, timedelta
from unittest.mock import patch

from auth import AuthManager, TokenData, require_auth

@pytest.fixture
def setup_env():
    """Setup test environment"""
    os.environ['ENV'] = 'test'
    os.environ['JWT_SECRET_KEY'] = 'test-secret-key'
    os.environ['INITIAL_TOKEN'] = 'test-initial-token'
    yield
    # Cleanup
    for key in ['ENV', 'JWT_SECRET_KEY', 'INITIAL_TOKEN']:
        if key in os.environ:
            del os.environ[key]

class TestAuthManager:
    def test_init_with_secret_key(self, setup_env):
        """Test initialization with secret key"""
        auth_manager = AuthManager()
        assert auth_manager.secret_key == 'test-secret-key'
        assert auth_manager.algorithm == 'HS256'
        
    def test_init_without_secret_key_dev(self, setup_env):
        """Test initialization without secret key in dev"""
        del os.environ['JWT_SECRET_KEY']
        os.environ['ENV'] = 'development'
        
        auth_manager = AuthManager()
        assert auth_manager.secret_key is not None
        assert len(auth_manager.secret_key) > 20
        
    def test_init_without_secret_key_prod(self, setup_env):
        """Test initialization without secret key in production"""
        del os.environ['JWT_SECRET_KEY']
        os.environ['ENV'] = 'production'
        
        with pytest.raises(ValueError, match="JWT_SECRET_KEY must be set"):
            AuthManager()
            
    def test_verify_initial_token(self, setup_env):
        """Test initial token verification"""
        auth_manager = AuthManager()
        
        # Correct token
        assert auth_manager.verify_initial_token('test-initial-token')
        
        # Wrong token
        assert not auth_manager.verify_initial_token('wrong-token')
        
        # Empty token
        assert not auth_manager.verify_initial_token('')
        
    def test_create_auth_token(self, setup_env):
        """Test JWT token creation"""
        auth_manager = AuthManager()
        
        token, expires = auth_manager.create_auth_token(
            user_id='test_user',
            project='test_project',
            expiry_minutes=60,
            permissions=['read', 'write']
        )
        
        assert isinstance(token, str)
        assert isinstance(expires, datetime)
        assert expires > datetime.utcnow()
        
        # Decode token to verify contents
        payload = jwt.decode(token, auth_manager.secret_key, algorithms=['HS256'])
        assert payload['user_id'] == 'test_user'
        assert payload['project'] == 'test_project'
        assert payload['permissions'] == ['read', 'write']
        assert payload['iss'] == 'reproschema-server'
        
    def test_verify_auth_token_valid(self, setup_env):
        """Test verification of valid token"""
        auth_manager = AuthManager()
        
        token, _ = auth_manager.create_auth_token(
            user_id='test_user',
            project='test_project'
        )
        
        token_data = auth_manager.verify_auth_token(token)
        assert isinstance(token_data, TokenData)
        assert token_data.user_id == 'test_user'
        assert token_data.project == 'test_project'
        
    def test_verify_auth_token_with_bearer(self, setup_env):
        """Test verification with Bearer prefix"""
        auth_manager = AuthManager()
        
        token, _ = auth_manager.create_auth_token(
            user_id='test_user',
            project='test_project'
        )
        
        token_data = auth_manager.verify_auth_token(f'Bearer {token}')
        assert token_data is not None
        assert token_data.user_id == 'test_user'
        
    def test_verify_auth_token_expired(self, setup_env):
        """Test verification of expired token"""
        auth_manager = AuthManager()
        
        # Create expired token
        expired_token = jwt.encode(
            {
                'user_id': 'test_user',
                'project': 'test_project',
                'exp': datetime.utcnow() - timedelta(hours=1),
                'iat': datetime.utcnow() - timedelta(hours=2),
                'iss': 'reproschema-server'
            },
            auth_manager.secret_key,
            algorithm='HS256'
        )
        
        token_data = auth_manager.verify_auth_token(expired_token)
        assert token_data is None
        
    def test_verify_auth_token_invalid(self, setup_env):
        """Test verification of invalid token"""
        auth_manager = AuthManager()
        
        # Invalid token
        token_data = auth_manager.verify_auth_token('invalid-token')
        assert token_data is None
        
        # Token with wrong secret
        wrong_token = jwt.encode(
            {'user_id': 'test'},
            'wrong-secret',
            algorithm='HS256'
        )
        token_data = auth_manager.verify_auth_token(wrong_token)
        assert token_data is None
        
    def test_has_permission(self, setup_env):
        """Test permission checking"""
        auth_manager = AuthManager()
        
        token_data = TokenData(
            user_id='test_user',
            project='test_project',
            expires=datetime.utcnow() + timedelta(hours=1),
            permissions=['read', 'write']
        )
        
        assert auth_manager.has_permission(token_data, 'read')
        assert auth_manager.has_permission(token_data, 'write')
        assert not auth_manager.has_permission(token_data, 'delete')
        
    def test_refresh_token(self, setup_env):
        """Test token refresh"""
        auth_manager = AuthManager()
        
        # Create initial token
        initial_token, _ = auth_manager.create_auth_token(
            user_id='test_user',
            project='test_project',
            permissions=['read']
        )
        
        # Refresh it
        result = auth_manager.refresh_token(initial_token, expiry_minutes=120)
        assert result is not None
        
        new_token, new_expires = result
        assert isinstance(new_token, str)
        assert new_token != initial_token  # Should be different
        
        # Verify new token has same data
        token_data = auth_manager.verify_auth_token(new_token)
        assert token_data.user_id == 'test_user'
        assert token_data.project == 'test_project'
        assert token_data.permissions == ['read']

class TestRequireAuthDecorator:
    @pytest.mark.asyncio
    async def test_require_auth_no_header(self, setup_env):
        """Test decorator with no auth header"""
        from sanic import Request
        from unittest.mock import MagicMock
        
        @require_auth()
        async def protected_endpoint(request):
            return {'data': 'protected'}
        
        # Mock request without auth header
        request = MagicMock()
        request.headers = {}
        
        response = await protected_endpoint(request)
        assert response.status == 401
        assert 'Authorization header required' in str(response.body)
        
    @pytest.mark.asyncio  
    async def test_require_auth_valid_token(self, setup_env):
        """Test decorator with valid token"""
        from unittest.mock import MagicMock, AsyncMock
        
        auth_manager = AuthManager()
        token, _ = auth_manager.create_auth_token('test_user', 'test_project')
        
        @require_auth()
        async def protected_endpoint(request):
            return {'data': 'protected', 'user': request.ctx.token_data.user_id}
        
        # Mock request with valid token
        request = MagicMock()
        request.headers = {'Authorization': f'Bearer {token}'}
        request.app.ctx.auth_manager = auth_manager
        request.ctx = MagicMock()
        
        # Call the wrapped function
        response = await protected_endpoint(request)
        assert response['data'] == 'protected'
        assert hasattr(request.ctx, 'token_data')
        
    @pytest.mark.asyncio
    async def test_require_auth_with_permission(self, setup_env):
        """Test decorator with permission requirement"""
        from unittest.mock import MagicMock
        
        auth_manager = AuthManager()
        token, _ = auth_manager.create_auth_token(
            'test_user', 
            'test_project',
            permissions=['read']
        )
        
        @require_auth('write')
        async def protected_endpoint(request):
            return {'data': 'protected'}
        
        # Mock request with token lacking required permission
        request = MagicMock()
        request.headers = {'Authorization': f'Bearer {token}'}
        request.app.ctx.auth_manager = auth_manager
        
        response = await protected_endpoint(request)
        assert response.status == 403
        # The response body is JSON, so we need to decode it
        import json
        error_data = json.loads(response.body)
        assert "Permission 'write' required" in error_data['error']