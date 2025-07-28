# 1. Backend stage - get token
FROM python:3.11-slim as backend-builder
WORKDIR /build
COPY docker/backend/. .
RUN pip install --no-cache-dir sanic sanic-ext requests jsonschema uuid PyJWT bcrypt

# Set environment variables for token generation
ENV JWT_SECRET_KEY=build-time-secret
ENV INITIAL_TOKEN=build-time-token
ENV ENV=development

# Generate a token for the build
RUN python -c "import uuid; print(uuid.uuid4().hex)" > /tmp/token && \
    echo "Generated token: $(cat /tmp/token)"

# 2. Frontend stage
FROM node:18-alpine as frontend-builder
WORKDIR /app

# Accept build args
ARG SCHEMA_SOURCE
ARG ASSETS_PUBLIC_PATH
ENV SCHEMA_SOURCE=${SCHEMA_SOURCE}
ENV ASSETS_PUBLIC_PATH=${ASSETS_PUBLIC_PATH}

# Install git and bash
RUN apk add --no-cache git bash curl

# Clone repo and copy files
RUN git clone https://github.com/ReproNim/reproschema-ui.git .
COPY docker/frontend/src/config.js src/
COPY scripts/setup-config.sh ./setup-config.sh
RUN chmod +x setup-config.sh

# 3. Set up config with everything we need
COPY --from=backend-builder /tmp/token /tmp/token
RUN INITIAL_TOKEN=$(cat /tmp/token) && \
    echo "Got token: $INITIAL_TOKEN" && \
    echo "INITIAL_TOKEN=$INITIAL_TOKEN" >> /tmp/env_vars
ENV BACKEND_URL="/api"

# 4. Run setup-config.sh to prepare config
RUN ./setup-config.sh

# 5. Now build with complete config
RUN npm install
RUN cat src/config.js  # Verify config before build
RUN npm run build
RUN find dist/js -type f -name "*.js" -exec grep -l "githubSrc" {} \;  # Find which bundle has our config

# Verify what's happening
RUN echo "=== Source config.js ===" && cat src/config.js
RUN echo "=== Dist files ===" && ls -la dist/
RUN echo "=== Dist directory structure ===" && find dist/
RUN echo "=== Dist config.js ===" && cat dist/config.js || echo "No config.js in dist!"

# Final image
FROM python:3.11-slim
WORKDIR /app

# Get assets path and token from frontend stage
COPY --from=frontend-builder /tmp/assets_path /tmp/assets_path
COPY --from=frontend-builder /tmp/token /tmp/token
# These will be read at runtime by the start script
# ENV commands don't support shell substitution

# Install nginx and other required packages
RUN apt-get update && \
    apt-get install -y nginx git uuid-runtime curl openssl gettext-base && \
    rm -rf /var/lib/apt/lists/* && \
    rm -f /etc/nginx/sites-enabled/default

# Install Python dependencies
RUN pip install --no-cache-dir sanic sanic-ext requests jsonschema uuid PyJWT bcrypt

# Copy frontend files
COPY --from=frontend-builder /app/dist /usr/share/nginx/html/

# Copy backend files
COPY docker/backend/app.py ./
COPY docker/backend/config.py ./
COPY docker/backend/auth.py ./
COPY docker/backend/validation.py ./
COPY docker/backend/logging_config.py ./
COPY scripts scripts
COPY config/nginx/default.conf /etc/nginx/conf.d/default.conf.template
RUN envsubst '${ASSETS_PUBLIC_PATH}' < /etc/nginx/conf.d/default.conf.template > /etc/nginx/conf.d/default.conf

# Copy SSL setup script and make it executable
COPY config/ssl/setup-ssl.sh /app/scripts/
RUN chmod +x /app/scripts/setup-ssl.sh

# Create SSL directory
RUN mkdir -p /etc/nginx/ssl

# Create app user for security
RUN useradd -m -u 1000 -s /bin/bash appuser

# Create necessary directories with proper permissions
RUN mkdir -p /schemas /data && \
    mkdir -p /data/responses && \
    chown -R appuser:appuser /data && \
    chmod -R 755 /data  # Secure permissions - owner can write, others can only read

# Environment variables
ENV REPROSCHEMA_BACKEND_BASEDIR=/data
ENV PORT=8000

# Make scripts executable
RUN chmod +x /app/scripts/*.sh && ls -la /app/scripts/

EXPOSE 80 8000
CMD ["/app/scripts/start.sh"]