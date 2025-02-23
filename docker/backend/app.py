from sanic import Sanic, json
from sanic.response import text
from sanic_ext import Extend
from pathlib import Path
import json as json_lib
import requests
from urllib.parse import urlparse
from datetime import datetime, timedelta
import uuid
import os

from config import (
    SCHEMA_DIR,
    RESPONSE_DIR,
    ALLOWED_ORIGINS
)

app = Sanic("reproschema_backend")
Extend(app)

@app.get("/api/health")
async def health_check(request):
    print("Health check requested")
    return json({"status": "healthy"})

# Token storage
tokens = {}
auth_tokens = {}

# Get initial token from environment or generate new one
INITIAL_TOKEN = os.getenv('INITIAL_TOKEN')
if not INITIAL_TOKEN:
    INITIAL_TOKEN = str(uuid.uuid4().hex)
    print(f"Warning: INITIAL_TOKEN not set, generated: {INITIAL_TOKEN}")
else:
    print(f"Using INITIAL_TOKEN from environment: {INITIAL_TOKEN}")

@app.get("/api/token")
async def get_token(request):
    token = request.args.get('token')
    project = request.args.get('project', os.getenv('STUDY_PREFIX', 'study'))
    expiry_minutes = int(request.args.get('expiry_minutes', 90))
    
    if token != INITIAL_TOKEN:
        return json({"error": "Invalid token"}, status=401)
    
    auth_token = f"{project}-{uuid.uuid4().hex}"
    expires = datetime.utcnow() + timedelta(minutes=expiry_minutes)
    
    auth_tokens[auth_token] = {
        "expires": expires,
        "project": project
    }
    
    return json({
        "auth_token": auth_token,
        "expires": expires.strftime("%Y%m%dT%H%M%SZ")
    })

# Add register endpoint for local development
@app.get("/api/register")
async def register(request):
    if not os.getenv('DEV_MODE'):
        return json({"error": "Registration only available in dev mode"}, status=403)
    
    token = request.args.get('token')
    callback_url = request.args.get('callback_url')
    
    if token != INITIAL_TOKEN:
        return json({"error": "Invalid token"}, status=401)
        
    return json({"status": "registered", "callback_url": callback_url})

@app.post("/api/responses")
async def submit_data(request):
    auth_token = request.headers.get('Authorization')
    
    # Strip "Bearer " prefix if present
    if auth_token and auth_token.startswith('Bearer '):
        auth_token = auth_token.split(' ')[1]
    
    if not auth_token or auth_token not in auth_tokens:
        return json({"error": "Invalid auth token"}, status=401)
        
    token_data = auth_tokens[auth_token]
    if datetime.utcnow() > token_data["expires"]:
        del auth_tokens[auth_token]
        return json({"error": "Token expired"}, status=401)

    try:
        project = token_data["project"]
        project_dir = RESPONSE_DIR / project
        project_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        response_file = project_dir / f"response_{timestamp}.json"
        
        with open(response_file, 'w') as f:
            json_lib.dump(request.json, f)
        return json({"status": "success"})
    except Exception as e:
        return json({"error": str(e)}, status=500)

@app.get("/api/schema/<url:path>")
async def get_schema(request, url):
    parsed_url = urlparse(url)
    base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
    
    if not any(origin in base_url for origin in ALLOWED_ORIGINS):
        return json({"error": "Origin not allowed"}, status=403)
    
    try:
        if url.startswith('http'):
            response = requests.get(url)
            response.raise_for_status()
            return json(response.json())
        else:
            schema_path = SCHEMA_DIR / url
            if not schema_path.exists():
                return json({"error": "Schema not found"}, status=404)
            with open(schema_path) as f:
                return json(json_lib.load(f))
    except requests.exceptions.RequestException as e:
        return json({"error": f"Failed to fetch schema: {str(e)}"}, status=503)
    except Exception as e:
        return json({"error": str(e)}, status=500)

@app.get("/")
async def root(request):
    return json({
        "status": "running",
        "endpoints": [
            "/api/health",
            "/api/token",
            "/api/responses",
            "/api/schema/<url>"
        ]
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)