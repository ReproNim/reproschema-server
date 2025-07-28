"""
Improved ReproSchema Server with enhanced security and structure
"""
import os
import uuid
import json
from datetime import datetime
from typing import Dict, Any
from pathlib import Path

from sanic import Sanic, json as sanic_json
from sanic.response import JSONResponse
from sanic_ext import Extend
import requests

# Local imports
from config import SCHEMA_DIR, RESPONSE_DIR, ALLOWED_ORIGINS
from auth import AuthManager, require_auth
from validation import DataValidator, ValidationError, validate_request_json
from logging_config import setup_logging, get_logger, RequestLogger

# Setup logging
setup_logging()
logger = get_logger('app')

# Initialize Sanic app
app = Sanic("reproschema_backend")
Extend(app)

# Initialize authentication manager
app.ctx.auth_manager = AuthManager()

# Middleware for request logging
@app.middleware('request')
async def add_request_id(request):
    """Add unique request ID for tracking"""
    request.ctx.request_id = str(uuid.uuid4())
    request.ctx.start_time = datetime.utcnow()

@app.middleware('response')
async def log_response(request, response):
    """Log response details"""
    duration = (datetime.utcnow() - request.ctx.start_time).total_seconds()
    
    with RequestLogger(request.ctx.request_id):
        logger.info(
            f"{request.method} {request.path} - "
            f"Status: {response.status} - "
            f"Duration: {duration:.3f}s"
        )

# Error handlers
@app.exception(ValidationError)
async def validation_error_handler(request, exception):
    """Handle validation errors gracefully"""
    with RequestLogger(getattr(request.ctx, 'request_id', 'unknown')):
        logger.warning(f"Validation error: {str(exception)}")
    
    return sanic_json({"error": str(exception)}, status=400)

@app.exception(Exception)
async def generic_error_handler(request, exception):
    """Handle unexpected errors"""
    with RequestLogger(getattr(request.ctx, 'request_id', 'unknown')):
        logger.error(f"Unexpected error: {str(exception)}", exc_info=True)
    
    return sanic_json({"error": "Internal server error"}, status=500)

# Health endpoints
@app.get("/health")
async def health_check_legacy(request) -> JSONResponse:
    """Legacy health check endpoint - redirects to /api/health"""
    return await health_check(request)

@app.get("/api/health")
async def health_check(request) -> JSONResponse:
    """Health check endpoint"""
    with RequestLogger(request.ctx.request_id):
        logger.debug("Health check requested")
    
    # Check if critical services are available
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat() + 'Z',
        "version": "1.0.0",
        "services": {
            "auth": "healthy",
            "storage": "healthy" if RESPONSE_DIR.exists() else "degraded",
            "schema": "healthy" if SCHEMA_DIR.exists() else "degraded"
        }
    }
    
    overall_status = 200
    if any(status == "degraded" for status in health_status["services"].values()):
        overall_status = 503
        health_status["status"] = "degraded"
    
    return sanic_json(health_status, status=overall_status)


# Authentication endpoints
@app.get("/api/token")
async def get_token(request) -> JSONResponse:
    """Get authentication token"""
    with RequestLogger(request.ctx.request_id):
        try:
            # Validate input parameters
            token = request.args.get('token')
            if not token:
                raise ValidationError("Token parameter is required")
            
            project = request.args.get('project', os.getenv('STUDY_PREFIX', 'study'))
            project = DataValidator.validate_project_name(project)
            
            expiry_minutes_raw = request.args.get('expiry_minutes', '90')
            expiry_minutes = DataValidator.validate_expiry_minutes(expiry_minutes_raw)
            
            # Verify initial token
            auth_manager = request.app.ctx.auth_manager
            if not auth_manager.verify_initial_token(token):
                logger.warning("Invalid initial token attempt")
                raise ValidationError("Invalid token")
            
            # Generate user ID (in production, this would come from proper user management)
            user_id = f"user_{uuid.uuid4().hex[:8]}"
            
            # Create JWT token
            auth_token, expires = auth_manager.create_auth_token(
                user_id=user_id,
                project=project,
                expiry_minutes=expiry_minutes
            )
            
            logger.info(f"Token created for project: {project}")
            
            return sanic_json({
                "auth_token": auth_token,
                "expires": expires.strftime("%Y%m%dT%H%M%SZ"),
                "project": project,
                "user_id": user_id
            })
            
        except ValidationError as e:
            raise e
        except Exception as e:
            logger.error(f"Token creation error: {str(e)}")
            raise ValidationError("Failed to create token")

@app.post("/api/token/refresh", name="refresh_token")
@require_auth()
async def refresh_token(request) -> JSONResponse:
    """Refresh an existing token"""
    with RequestLogger(request.ctx.request_id):
        try:
            auth_header = request.headers.get('Authorization')
            expiry_minutes_raw = request.json.get('expiry_minutes', 90) if request.json else 90
            expiry_minutes = DataValidator.validate_expiry_minutes(expiry_minutes_raw)
            
            auth_manager = request.app.ctx.auth_manager
            result = auth_manager.refresh_token(auth_header, expiry_minutes)
            
            if not result:
                raise ValidationError("Failed to refresh token")
            
            new_token, expires = result
            
            logger.info(f"Token refreshed for user: {request.ctx.token_data.user_id}")
            
            return sanic_json({
                "auth_token": new_token,
                "expires": expires.strftime("%Y%m%dT%H%M%SZ")
            })
            
        except ValidationError as e:
            raise e
        except Exception as e:
            logger.error(f"Token refresh error: {str(e)}")
            raise ValidationError("Failed to refresh token")

# Data submission endpoint
@app.post("/api/responses", name="submit_responses")
@require_auth('submit_responses')
async def submit_data(request) -> JSONResponse:
    """Submit response data"""
    with RequestLogger(request.ctx.request_id):
        try:
            # Validate and parse request data
            validated_data = validate_request_json(request)
            
            token_data = request.ctx.token_data
            project = token_data.project
            user_id = token_data.user_id
            
            # Create project directory
            project_dir = RESPONSE_DIR / project
            project_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate secure filename
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"response_{user_id}_{timestamp}_{uuid.uuid4().hex[:8]}.json"
            response_file = project_dir / filename
            
            # Add metadata
            response_data = {
                "metadata": {
                    "user_id": user_id,
                    "project": project,
                    "timestamp": datetime.utcnow().isoformat() + 'Z',
                    "request_id": request.ctx.request_id
                },
                "data": validated_data
            }
            
            # Write to file atomically
            temp_file = response_file.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                import json
                json.dump(response_data, f, indent=2, ensure_ascii=False)
            
            # Atomic rename
            temp_file.rename(response_file)
            
            logger.info(f"Response saved for user {user_id} in project {project}")
            
            return sanic_json({
                "status": "success",
                "response_id": filename.replace('.json', ''),
                "timestamp": response_data["metadata"]["timestamp"]
            })
            
        except ValidationError as e:
            raise e
        except Exception as e:
            logger.error(f"Data submission error: {str(e)}")
            raise ValidationError("Failed to save response")

# Schema endpoint
@app.get("/api/schema/<url:path>", name="get_schema")
@require_auth('read_schema')
async def get_schema(request, url: str) -> JSONResponse:
    """Get schema from URL or local file"""
    with RequestLogger(request.ctx.request_id):
        try:
            # Validate URL if it's a web URL
            if url.startswith('http'):
                validated_url = DataValidator.validate_schema_url(url)
                
                # Check if origin is allowed
                from urllib.parse import urlparse
                parsed_url = urlparse(validated_url)
                base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
                
                if not any(origin in base_url for origin in ALLOWED_ORIGINS if origin):
                    logger.warning(f"Blocked request to unauthorized origin: {base_url}")
                    raise ValidationError("Origin not allowed")
                
                # Fetch from URL with timeout and size limits
                try:
                    response = requests.get(
                        validated_url,
                        timeout=30,
                        headers={'User-Agent': 'ReproSchema-Server/1.0'}
                    )
                    response.raise_for_status()
                    
                    # Check response size
                    if len(response.content) > DataValidator.MAX_JSON_SIZE:
                        raise ValidationError("Schema file too large")
                    
                    schema_data = response.json()
                    
                except requests.exceptions.RequestException as e:
                    logger.error(f"Failed to fetch schema from {validated_url}: {str(e)}")
                    raise ValidationError(f"Failed to fetch schema: {str(e)}")
                    
            else:
                # Local file access
                sanitized_path = DataValidator.sanitize_filename(url)
                schema_path = SCHEMA_DIR / sanitized_path
                
                # Prevent directory traversal
                if not str(schema_path.resolve()).startswith(str(SCHEMA_DIR.resolve())):
                    raise ValidationError("Invalid file path")
                
                if not schema_path.exists():
                    raise ValidationError("Schema not found")
                
                try:
                    with open(schema_path, 'r', encoding='utf-8') as f:
                        schema_data = json.load(f)
                except Exception as e:
                    logger.error(f"Failed to read schema file {schema_path}: {str(e)}")
                    raise ValidationError("Failed to read schema file")
            
            logger.info(f"Schema served: {url}")
            return sanic_json(schema_data)
            
        except ValidationError as e:
            raise e
        except Exception as e:
            logger.error(f"Schema retrieval error: {str(e)}")
            raise ValidationError("Failed to retrieve schema")

# Registration endpoint (dev mode only)
@app.get("/api/register")
async def register(request) -> JSONResponse:
    """Register callback URL (development mode only)"""
    with RequestLogger(request.ctx.request_id):
        if not os.getenv('DEV_MODE'):
            raise ValidationError("Registration only available in development mode")
        
        try:
            token = request.args.get('token')
            callback_url = request.args.get('callback_url')
            
            if not token or not callback_url:
                raise ValidationError("Token and callback_url parameters required")
            
            auth_manager = request.app.ctx.auth_manager
            if not auth_manager.verify_initial_token(token):
                raise ValidationError("Invalid token")
            
            # Validate callback URL
            validated_callback = DataValidator.validate_schema_url(callback_url)
            
            logger.info(f"Registration successful for callback: {validated_callback}")
            
            return sanic_json({
                "status": "registered",
                "callback_url": validated_callback
            })
            
        except ValidationError as e:
            raise e
        except Exception as e:
            logger.error(f"Registration error: {str(e)}")
            raise ValidationError("Registration failed")

# Root endpoint
@app.get("/")
async def root(request) -> JSONResponse:
    """API information endpoint"""
    return sanic_json({
        "name": "ReproSchema Server",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/api/health",
            "authentication": "/api/token",
            "refresh": "/api/token/refresh",
            "responses": "/api/responses",
            "schema": "/api/schema/<url>",
            "register": "/api/register (dev mode only)"
        },
        "documentation": "/docs"
    })

if __name__ == "__main__":
    # Production deployment should use a proper WSGI server
    logger.info("Starting ReproSchema Server")
    app.run(
        host="0.0.0.0",
        port=8000,
        debug=os.getenv('DEBUG', 'false').lower() == 'true',
        auto_reload=os.getenv('AUTO_RELOAD', 'false').lower() == 'true',
        single_process=True  # Required for Docker
    )