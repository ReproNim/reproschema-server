# Deployment Guide

This guide explains how to deploy the ReproSchema system in different environments.

## Overview

The deployment system consists of three Docker Compose configurations:
- `docker-compose.yml` - Base configuration
- `docker-compose.dev.yml` - Development environment settings
- `docker-compose.prod.yml` - Production environment settings

## Quick Start

### Development Environment

For local development with hot reloading and debugging:

```bash
# Copy and configure environment variables
cp .env.example .env
# Edit .env file with your settings

# Start development environment
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

Development environment provides:
- Hot reloading for frontend changes
- Source code mounting for live development
- Local directory for participant data
- Debug mode enabled
- Direct access to Vue dev server (no nginx)

### Production Environment

For deploying to production servers:

```bash
# Copy and configure environment variables
cp .env.example .env
# Edit .env file with your production settings

# Start production environment
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

Production environment provides:
- Optimized builds
- SSL configuration
- Nginx reverse proxy
- Automatic container restart
- Proper volume management for data persistence

## Schema Configuration

You can use schemas in two ways:

1. Remote Schema (GitHub):
```env
SCHEMA_URL=https://raw.githubusercontent.com/your-org/your-schema/main/protocol_schema
```

2. Local Schema:
```env
SCHEMA_URL=http://localhost/schema
LOCAL_SCHEMA_DIR=/path/to/your/local/schema
```

## Environment Variables

Key environment variables:

```env
# Schema Configuration
SCHEMA_URL=                 # URL to your schema
LOCAL_SCHEMA_DIR=          # Path to local schema directory (optional)

# Service Ports
FRONTEND_PORT=3000         # Frontend service port
BACKEND_PORT=8000          # Backend service port
PORT=80                    # Nginx HTTP port
SSL_PORT=443               # Nginx HTTPS port

# Environment Settings
NODE_ENV=production        # Node environment
DEV_MODE=0                # Backend development mode
PROJECT_NAME=default      # Project identifier

# Nginx Settings
NGINX_HOST=localhost      # Nginx host name
```

## Data Management

Participant data is stored in Docker volumes:

- Development: Mounted to local directory (`./dev-data`)
- Production: Uses Docker named volume (`participant_data`)

Access production data:
```bash
# List data volumes
docker volume ls

# Inspect data volume
docker volume inspect participant_data

# Backup data
docker run --rm -v participant_data:/data -v $(pwd):/backup alpine tar czf /backup/participant_data.tar.gz /data
```

## SSL Configuration

For production deployments with SSL:

1. Place SSL certificates in `config/ssl/`:
   - `config/ssl/cert.pem`
   - `config/ssl/key.pem`

2. Update nginx configuration in `config/nginx/prod.conf`

## Common Operations

### View Logs
```bash
# Development logs
docker compose -f docker-compose.yml -f docker-compose.dev.yml logs -f

# Production logs
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f
```

### Update Deployment
```bash
# Pull latest changes
git pull

# Rebuild and restart (production)
docker compose -f docker-compose.yml -f docker-compose.prod.yml build
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### Stop Services
```bash
# Development
docker compose -f docker-compose.yml -f docker-compose.dev.yml down

# Production
docker compose -f docker-compose.yml -f docker-compose.prod.yml down
```

## Troubleshooting

Common issues and solutions:

1. Schema not loading:
   - Check SCHEMA_URL is accessible
   - Verify LOCAL_SCHEMA_DIR permissions
   - Check nginx configuration if using local schema

2. Data not persisting:
   - Verify volume configuration
   - Check directory permissions
   - Inspect Docker volume status

3. Frontend not updating:
   - Clear browser cache
   - Check hot reload configuration in development
   - Verify source code mounting in development

4. Backend connection issues:
   - Verify ports are not in use
   - Check network configuration
   - Validate CORS settings