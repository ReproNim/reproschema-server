"""
Input validation and data sanitization for ReproSchema Server
Ensures data integrity and prevents injection attacks
"""
import re
import json
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class ValidationError(Exception):
    """Custom validation error"""
    pass

class DataValidator:
    """Comprehensive data validation"""
    
    # Regex patterns for validation
    PROJECT_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9_-]+$')
    USER_ID_PATTERN = re.compile(r'^[a-zA-Z0-9_.-]+$')
    SCHEMA_URL_PATTERN = re.compile(r'^https?://[^\s<>"{}|\\^`\[\]]+$')
    
    # Max sizes to prevent DoS
    MAX_JSON_SIZE = 10 * 1024 * 1024  # 10MB
    MAX_STRING_LENGTH = 10000
    MAX_ARRAY_LENGTH = 1000
    MAX_OBJECT_DEPTH = 10
    
    @classmethod
    def validate_project_name(cls, project_name: str) -> str:
        """Validate project name format"""
        if not project_name:
            raise ValidationError("Project name is required")
        
        if len(project_name) > 50:
            raise ValidationError("Project name too long (max 50 characters)")
            
        if not cls.PROJECT_NAME_PATTERN.match(project_name):
            raise ValidationError("Project name can only contain letters, numbers, hyphens, and underscores")
        
        return project_name.strip()
    
    @classmethod
    def validate_user_id(cls, user_id: str) -> str:
        """Validate user ID format"""
        if not user_id:
            raise ValidationError("User ID is required")
        
        if len(user_id) > 100:
            raise ValidationError("User ID too long (max 100 characters)")
            
        if not cls.USER_ID_PATTERN.match(user_id):
            raise ValidationError("User ID contains invalid characters")
        
        return user_id.strip()
    
    @classmethod
    def validate_schema_url(cls, url: str) -> str:
        """Validate schema URL format and safety"""
        if not url:
            raise ValidationError("URL is required")
        
        if len(url) > 2000:
            raise ValidationError("URL too long (max 2000 characters)")
        
        # Parse URL to validate structure
        try:
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                raise ValidationError("Invalid URL format")
                
            if parsed.scheme not in ['http', 'https']:
                raise ValidationError("Only HTTP/HTTPS URLs allowed")
                
        except Exception as e:
            raise ValidationError(f"Invalid URL: {str(e)}")
        
        return url.strip()
    
    @classmethod
    def validate_response_data(cls, data: Any, depth: int = 0) -> Any:
        """Recursively validate response data structure"""
        if depth > cls.MAX_OBJECT_DEPTH:
            raise ValidationError(f"Data structure too deep (max depth: {cls.MAX_OBJECT_DEPTH})")
        
        if isinstance(data, dict):
            if len(data) > cls.MAX_ARRAY_LENGTH:
                raise ValidationError(f"Object has too many keys (max: {cls.MAX_ARRAY_LENGTH})")
            
            validated = {}
            for key, value in data.items():
                # Validate key
                if not isinstance(key, str):
                    raise ValidationError("Object keys must be strings")
                if len(key) > cls.MAX_STRING_LENGTH:
                    raise ValidationError(f"Key too long: {key[:50]}...")
                
                # Recursively validate value
                validated[key] = cls.validate_response_data(value, depth + 1)
            
            return validated
        
        elif isinstance(data, list):
            if len(data) > cls.MAX_ARRAY_LENGTH:
                raise ValidationError(f"Array too long (max: {cls.MAX_ARRAY_LENGTH})")
            
            return [cls.validate_response_data(item, depth + 1) for item in data]
        
        elif isinstance(data, str):
            if len(data) > cls.MAX_STRING_LENGTH:
                raise ValidationError(f"String too long (max: {cls.MAX_STRING_LENGTH})")
            
            # Basic XSS prevention
            if '<script' in data.lower() or 'javascript:' in data.lower():
                raise ValidationError("Potentially unsafe content detected")
            
            return data
        
        elif isinstance(data, (int, float, bool)) or data is None:
            return data
        
        else:
            raise ValidationError(f"Unsupported data type: {type(data)}")
    
    @classmethod
    def validate_json_size(cls, json_data: str) -> None:
        """Check JSON size before parsing"""
        if len(json_data) > cls.MAX_JSON_SIZE:
            raise ValidationError(f"JSON too large (max: {cls.MAX_JSON_SIZE} bytes)")
    
    @classmethod
    def sanitize_filename(cls, filename: str) -> str:
        """Sanitize filename for safe storage"""
        if not filename:
            raise ValidationError("Filename is required")
        
        # Remove dangerous characters
        sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
        sanitized = re.sub(r'\.\.', '_', sanitized)  # Prevent directory traversal
        
        if len(sanitized) > 255:
            # Keep extension if possible
            name, ext = os.path.splitext(sanitized)
            sanitized = name[:255-len(ext)] + ext
        
        if not sanitized or sanitized.startswith('.'):
            raise ValidationError("Invalid filename")
        
        return sanitized
    
    @classmethod
    def validate_expiry_minutes(cls, expiry_minutes: Union[str, int]) -> int:
        """Validate token expiry time"""
        try:
            minutes = int(expiry_minutes)
        except (ValueError, TypeError):
            raise ValidationError("Expiry minutes must be a number")
        
        if minutes < 1:
            raise ValidationError("Expiry minutes must be positive")
        
        if minutes > 10080:  # 1 week
            raise ValidationError("Expiry minutes too large (max: 1 week)")
        
        return minutes

def validate_request_json(request) -> Dict[str, Any]:
    """Validate and parse request JSON safely"""
    try:
        # Check content type
        content_type = request.headers.get('content-type', '')
        if not content_type.startswith('application/json'):
            raise ValidationError("Content-Type must be application/json")
        
        # Get raw body and check size
        raw_body = request.body
        if not raw_body:
            raise ValidationError("Request body is empty")
        
        DataValidator.validate_json_size(raw_body.decode('utf-8'))
        
        # Parse JSON
        data = json.loads(raw_body)
        
        # Validate structure
        validated_data = DataValidator.validate_response_data(data)
        
        return validated_data
        
    except json.JSONDecodeError as e:
        raise ValidationError(f"Invalid JSON: {str(e)}")
    except UnicodeDecodeError:
        raise ValidationError("Invalid character encoding")
    except Exception as e:
        if isinstance(e, ValidationError):
            raise
        logger.error(f"Unexpected validation error: {e}")
        raise ValidationError("Invalid request data")