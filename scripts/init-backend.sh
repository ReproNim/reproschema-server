#!/bin/bash

set -e

# Initialize schema based on source
if [ "$SCHEMA_SOURCE" = "github" ]; then
   echo "Fetching schema from GitHub repository..."
   if [ -z "$GITHUB_REPO" ]; then
       echo "Error: GITHUB_REPO must be set when SCHEMA_SOURCE=github"
       exit 1
   fi
   
   # Clone repository if token is provided
   if [ -n "$GITHUB_TOKEN" ]; then
       git clone https://x-access-token:${GITHUB_TOKEN}@github.com/${GITHUB_REPO} /tmp/schema
   else
       git clone https://github.com/${GITHUB_REPO} /tmp/schema
   fi
   
   # Copy schema files
   cp -r /tmp/schema/* ${REPROSCHEMA_BACKEND_BASEDIR}/schemas/
   rm -rf /tmp/schema
else
   echo "Using local schema from mounted volume..."
fi

# Generate initial token if not provided
if [ -z "$INITIAL_TOKEN" ]; then
   export INITIAL_TOKEN=$(uuidgen)
   echo "Generated initial token: $INITIAL_TOKEN"
fi

# Start the application using Sanic
python -m sanic backend.app:app --host=0.0.0.0 --port=8000 --workers=4