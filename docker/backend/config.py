import os
from pathlib import Path

# Base directory paths
BACKEND_BASEDIR = os.getenv('REPROSCHEMA_BACKEND_BASEDIR', '/data')
SCHEMA_DIR = Path(BACKEND_BASEDIR) / 'schemas'
RESPONSE_DIR = Path(BACKEND_BASEDIR) / 'responses'

# Authentication - remove JWT, add token auth
INITIAL_TOKEN = os.getenv('INITIAL_TOKEN')
DEV_MODE = os.getenv('DEV8dac6d02a913', '0')

# Schema sources and security 
ALLOWED_ORIGINS = [
   'https://raw.githubusercontent.com',
   os.getenv('CUSTOM_SCHEMA_ORIGIN')
]

# Schema configuration
SCHEMA_SOURCE = os.getenv('SCHEMA_SOURCE', 'local')
GITHUB_REPO = os.getenv('GITHUB_REPO')
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')