#!/bin/bash
set -e

# Enhanced logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Initialize directories
mkdir -p /data/responses

# Configure nginx with assets path
if [ -f /tmp/assets_path ]; then
    export ASSETS_PUBLIC_PATH="$(cat /tmp/assets_path)"
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Configuring nginx with ASSETS_PUBLIC_PATH=${ASSETS_PUBLIC_PATH}"

# Configure nginx with correct path
envsubst '${ASSETS_PUBLIC_PATH}' < /etc/nginx/conf.d/default.conf.template > /etc/nginx/conf.d/default.conf
log "Nginx config:"
cat /etc/nginx/conf.d/default.conf | grep -A 5 "location.*${ASSETS_PUBLIC_PATH}"

# Setup SSL certificates
/app/scripts/setup-ssl.sh

# Start nginx
log "Starting nginx..."
nginx

# Start backend
log "Starting Python backend..."
python app.py &
BACKEND_PID=$!

# Wait for backend to be ready
log "Waiting for backend to be ready..."
ATTEMPTS=0
MAX_ATTEMPTS=30
until curl -s http://localhost:8000/health > /dev/null; do
    ATTEMPTS=$((ATTEMPTS + 1))
    if [ $ATTEMPTS -ge $MAX_ATTEMPTS ]; then
        log "Backend failed to start after $MAX_ATTEMPTS attempts"
        exit 1
    fi
    log "Attempt $ATTEMPTS: Backend not ready yet..."
    sleep 1
done
log "Backend is ready"

# Wait for processes
wait $BACKEND_PID