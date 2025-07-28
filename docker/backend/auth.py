"""
Authentication and authorization module for ReproSchema Server
Implements secure token management and user authentication
"""
import os
import jwt
import bcrypt
import secrets
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class TokenData:
    """Token metadata"""
    user_id: str
    project: str
    expires: datetime
    permissions: list

class AuthManager:
    """Secure authentication manager"""
    
    def __init__(self):
        self.secret_key = os.getenv('JWT_SECRET_KEY')
        if not self.secret_key:
            if os.getenv('ENV', 'production').lower() == 'production':
                raise ValueError("JWT_SECRET_KEY must be set in production environment")
            # Only generate temporary key in development
            self.secret_key = secrets.token_urlsafe(32)
            logger.warning("JWT_SECRET_KEY not set, using generated key (development only)")
        
        self.initial_token_hash = self._get_initial_token_hash()
        self.algorithm = 'HS256'
        
    def _get_initial_token_hash(self) -> bytes:
        """Get hashed initial token from environment"""
        initial_token = os.getenv('INITIAL_TOKEN')
        if not initial_token:
            # Generate a secure initial token
            initial_token = secrets.token_urlsafe(32)
            logger.warning(f"INITIAL_TOKEN not set, generated: {initial_token}")
        
        return bcrypt.hashpw(initial_token.encode('utf-8'), bcrypt.gensalt())
    
    def verify_initial_token(self, token: str) -> bool:
        """Verify the initial authentication token"""
        try:
            return bcrypt.checkpw(token.encode('utf-8'), self.initial_token_hash)
        except Exception as e:
            logger.error(f"Token verification error: {e}")
            return False
    
    def create_auth_token(
        self, 
        user_id: str, 
        project: str, 
        expiry_minutes: int = 90,
        permissions: list = None
    ) -> Tuple[str, datetime]:
        """Create a secure JWT token"""
        if permissions is None:
            permissions = ['read_schema', 'submit_responses']
            
        expires = datetime.utcnow() + timedelta(minutes=expiry_minutes)
        
        payload = {
            'user_id': user_id,
            'project': project,
            'permissions': permissions,
            'exp': expires,
            'iat': datetime.utcnow(),
            'iss': 'reproschema-server'
        }
        
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        return token, expires
    
    def verify_auth_token(self, token: str) -> Optional[TokenData]:
        """Verify and decode JWT token"""
        try:
            # Remove Bearer prefix if present
            if token.startswith('Bearer '):
                token = token.split(' ')[1]
                
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            return TokenData(
                user_id=payload['user_id'],
                project=payload['project'],
                expires=datetime.fromtimestamp(payload['exp']),
                permissions=payload.get('permissions', [])
            )
        except jwt.ExpiredSignatureError:
            logger.info("Token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return None
        except Exception as e:
            logger.error(f"Token verification error: {e}")
            return None
    
    def has_permission(self, token_data: TokenData, required_permission: str) -> bool:
        """Check if token has required permission"""
        return required_permission in token_data.permissions
    
    def refresh_token(self, current_token: str, expiry_minutes: int = 90) -> Optional[Tuple[str, datetime]]:
        """Refresh an existing valid token"""
        token_data = self.verify_auth_token(current_token)
        if not token_data:
            return None
            
        # Create new token with same permissions
        return self.create_auth_token(
            token_data.user_id,
            token_data.project,
            expiry_minutes,
            token_data.permissions
        )

def require_auth(permission: str = None):
    """Decorator for endpoints requiring authentication"""
    def decorator(func):
        async def wrapper(request, *args, **kwargs):
            from sanic import json as sanic_json
            
            auth_header = request.headers.get('Authorization')
            if not auth_header:
                return sanic_json({"error": "Authorization header required"}, status=401)
            
            auth_manager = request.app.ctx.auth_manager
            token_data = auth_manager.verify_auth_token(auth_header)
            
            if not token_data:
                return sanic_json({"error": "Invalid or expired token"}, status=401)
                
            if permission and not auth_manager.has_permission(token_data, permission):
                return sanic_json({"error": f"Permission '{permission}' required"}, status=403)
            
            # Add token data to request context
            request.ctx.token_data = token_data
            return await func(request, *args, **kwargs)
        
        return wrapper
    return decorator