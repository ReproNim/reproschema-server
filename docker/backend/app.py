"""
Improved ReproSchema Server with enhanced security and structure
"""
import os
import uuid
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

# Health endpoint
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
            expiry_minutes = DataValidator.validate_expiry_minutes(expiry_minutes_raw)\n            \n            # Verify initial token\n            auth_manager = request.app.ctx.auth_manager\n            if not auth_manager.verify_initial_token(token):\n                logger.warning(\"Invalid initial token attempt\")\n                raise ValidationError(\"Invalid token\")\n            \n            # Generate user ID (in production, this would come from proper user management)\n            user_id = f\"user_{uuid.uuid4().hex[:8]}\"\n            \n            # Create JWT token\n            auth_token, expires = auth_manager.create_auth_token(\n                user_id=user_id,\n                project=project,\n                expiry_minutes=expiry_minutes\n            )\n            \n            logger.info(f\"Token created for project: {project}\")\n            \n            return sanic_json({\n                \"auth_token\": auth_token,\n                \"expires\": expires.strftime(\"%Y%m%dT%H%M%SZ\"),\n                \"project\": project,\n                \"user_id\": user_id\n            })\n            \n        except ValidationError as e:\n            raise e\n        except Exception as e:\n            logger.error(f\"Token creation error: {str(e)}\")\n            raise ValidationError(\"Failed to create token\")\n\n@app.post(\"/api/token/refresh\")\n@require_auth()\nasync def refresh_token(request) -> JSONResponse:\n    \"\"\"Refresh an existing token\"\"\"\n    with RequestLogger(request.ctx.request_id):\n        try:\n            auth_header = request.headers.get('Authorization')\n            expiry_minutes_raw = request.json.get('expiry_minutes', 90) if request.json else 90\n            expiry_minutes = DataValidator.validate_expiry_minutes(expiry_minutes_raw)\n            \n            auth_manager = request.app.ctx.auth_manager\n            result = auth_manager.refresh_token(auth_header, expiry_minutes)\n            \n            if not result:\n                raise ValidationError(\"Failed to refresh token\")\n            \n            new_token, expires = result\n            \n            logger.info(f\"Token refreshed for user: {request.ctx.token_data.user_id}\")\n            \n            return sanic_json({\n                \"auth_token\": new_token,\n                \"expires\": expires.strftime(\"%Y%m%dT%H%M%SZ\")\n            })\n            \n        except ValidationError as e:\n            raise e\n        except Exception as e:\n            logger.error(f\"Token refresh error: {str(e)}\")\n            raise ValidationError(\"Failed to refresh token\")\n\n# Data submission endpoint\n@app.post(\"/api/responses\")\n@require_auth('submit_responses')\nasync def submit_data(request) -> JSONResponse:\n    \"\"\"Submit response data\"\"\"\n    with RequestLogger(request.ctx.request_id):\n        try:\n            # Validate and parse request data\n            validated_data = validate_request_json(request)\n            \n            token_data = request.ctx.token_data\n            project = token_data.project\n            user_id = token_data.user_id\n            \n            # Create project directory\n            project_dir = RESPONSE_DIR / project\n            project_dir.mkdir(parents=True, exist_ok=True)\n            \n            # Generate secure filename\n            timestamp = datetime.utcnow().strftime(\"%Y%m%d_%H%M%S\")\n            filename = f\"response_{user_id}_{timestamp}_{uuid.uuid4().hex[:8]}.json\"\n            response_file = project_dir / filename\n            \n            # Add metadata\n            response_data = {\n                \"metadata\": {\n                    \"user_id\": user_id,\n                    \"project\": project,\n                    \"timestamp\": datetime.utcnow().isoformat() + 'Z',\n                    \"request_id\": request.ctx.request_id\n                },\n                \"data\": validated_data\n            }\n            \n            # Write to file atomically\n            temp_file = response_file.with_suffix('.tmp')\n            with open(temp_file, 'w', encoding='utf-8') as f:\n                import json\n                json.dump(response_data, f, indent=2, ensure_ascii=False)\n            \n            # Atomic rename\n            temp_file.rename(response_file)\n            \n            logger.info(f\"Response saved for user {user_id} in project {project}\")\n            \n            return sanic_json({\n                \"status\": \"success\",\n                \"response_id\": filename.replace('.json', ''),\n                \"timestamp\": response_data[\"metadata\"][\"timestamp\"]\n            })\n            \n        except ValidationError as e:\n            raise e\n        except Exception as e:\n            logger.error(f\"Data submission error: {str(e)}\")\n            raise ValidationError(\"Failed to save response\")\n\n# Schema endpoint\n@app.get(\"/api/schema/<url:path>\")\n@require_auth('read_schema')\nasync def get_schema(request, url: str) -> JSONResponse:\n    \"\"\"Get schema from URL or local file\"\"\"\n    with RequestLogger(request.ctx.request_id):\n        try:\n            # Validate URL if it's a web URL\n            if url.startswith('http'):\n                validated_url = DataValidator.validate_schema_url(url)\n                \n                # Check if origin is allowed\n                from urllib.parse import urlparse\n                parsed_url = urlparse(validated_url)\n                base_url = f\"{parsed_url.scheme}://{parsed_url.netloc}\"\n                \n                if not any(origin in base_url for origin in ALLOWED_ORIGINS if origin):\n                    logger.warning(f\"Blocked request to unauthorized origin: {base_url}\")\n                    raise ValidationError(\"Origin not allowed\")\n                \n                # Fetch from URL with timeout and size limits\n                try:\n                    response = requests.get(\n                        validated_url,\n                        timeout=30,\n                        headers={'User-Agent': 'ReproSchema-Server/1.0'}\n                    )\n                    response.raise_for_status()\n                    \n                    # Check response size\n                    if len(response.content) > DataValidator.MAX_JSON_SIZE:\n                        raise ValidationError(\"Schema file too large\")\n                    \n                    schema_data = response.json()\n                    \n                except requests.exceptions.RequestException as e:\n                    logger.error(f\"Failed to fetch schema from {validated_url}: {str(e)}\")\n                    raise ValidationError(f\"Failed to fetch schema: {str(e)}\")\n                    \n            else:\n                # Local file access\n                sanitized_path = DataValidator.sanitize_filename(url)\n                schema_path = SCHEMA_DIR / sanitized_path\n                \n                # Prevent directory traversal\n                if not str(schema_path.resolve()).startswith(str(SCHEMA_DIR.resolve())):\n                    raise ValidationError(\"Invalid file path\")\n                \n                if not schema_path.exists():\n                    raise ValidationError(\"Schema not found\")\n                \n                try:\n                    with open(schema_path, 'r', encoding='utf-8') as f:\n                        schema_data = json.load(f)\n                except Exception as e:\n                    logger.error(f\"Failed to read schema file {schema_path}: {str(e)}\")\n                    raise ValidationError(\"Failed to read schema file\")\n            \n            logger.info(f\"Schema served: {url}\")\n            return sanic_json(schema_data)\n            \n        except ValidationError as e:\n            raise e\n        except Exception as e:\n            logger.error(f\"Schema retrieval error: {str(e)}\")\n            raise ValidationError(\"Failed to retrieve schema\")\n\n# Registration endpoint (dev mode only)\n@app.get(\"/api/register\")\nasync def register(request) -> JSONResponse:\n    \"\"\"Register callback URL (development mode only)\"\"\"\n    with RequestLogger(request.ctx.request_id):\n        if not os.getenv('DEV_MODE'):\n            raise ValidationError(\"Registration only available in development mode\")\n        \n        try:\n            token = request.args.get('token')\n            callback_url = request.args.get('callback_url')\n            \n            if not token or not callback_url:\n                raise ValidationError(\"Token and callback_url parameters required\")\n            \n            auth_manager = request.app.ctx.auth_manager\n            if not auth_manager.verify_initial_token(token):\n                raise ValidationError(\"Invalid token\")\n            \n            # Validate callback URL\n            validated_callback = DataValidator.validate_schema_url(callback_url)\n            \n            logger.info(f\"Registration successful for callback: {validated_callback}\")\n            \n            return sanic_json({\n                \"status\": \"registered\",\n                \"callback_url\": validated_callback\n            })\n            \n        except ValidationError as e:\n            raise e\n        except Exception as e:\n            logger.error(f\"Registration error: {str(e)}\")\n            raise ValidationError(\"Registration failed\")\n\n# Root endpoint\n@app.get(\"/\")\nasync def root(request) -> JSONResponse:\n    \"\"\"API information endpoint\"\"\"\n    return sanic_json({\n        \"name\": \"ReproSchema Server\",\n        \"version\": \"1.0.0\",\n        \"status\": \"running\",\n        \"endpoints\": {\n            \"health\": \"/api/health\",\n            \"authentication\": \"/api/token\",\n            \"refresh\": \"/api/token/refresh\",\n            \"responses\": \"/api/responses\",\n            \"schema\": \"/api/schema/<url>\",\n            \"register\": \"/api/register (dev mode only)\"\n        },\n        \"documentation\": \"/docs\"\n    })\n\nif __name__ == \"__main__\":\n    # Production deployment should use a proper WSGI server\n    logger.info(\"Starting ReproSchema Server\")\n    app.run(\n        host=\"0.0.0.0\",\n        port=8000,\n        debug=os.getenv('DEBUG', 'false').lower() == 'true',\n        auto_reload=os.getenv('AUTO_RELOAD', 'false').lower() == 'true'\n    )"