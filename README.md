# ReproSchema Deployment Container

A containerized solution for deploying ReproSchema UI with data collection capabilities. Simply provide your schema (either from GitHub or local files) and start collecting data.

## Quick Start

1. Create a `.env` file with your configuration:
```bash
# Required
PROJECT_NAME=my_study          # Name for your deployment
SCHEMA_SOURCE=local           # 'local' or 'github'

# For GitHub schemas
GITHUB_REPO=user/repo         # Only needed if SCHEMA_SOURCE=github
GITHUB_TOKEN=ghp_xxx         # Optional: for private repositories

# Optional
PORT=3000                    # Default: 3000
```

2. Start the container:

For local schema:
```bash
# Place your schema files in ./schemas directory
mkdir schemas
cp -r my-schema/* schemas/

# Start the container
docker compose up -d
```

For GitHub schema:
```bash
# Start with GitHub repository
SCHEMA_SOURCE=github GITHUB_REPO=user/repo docker compose up -d
```

3. Access the UI at `http://localhost:3000`

## Data Storage

Participant data is automatically stored in a Docker volume named `${PROJECT_NAME}_data`. To backup or export the data:

```bash
# Export data
docker run --rm -v ${PROJECT_NAME}_data:/data -v $(pwd):/backup alpine tar czf /backup/data.tar.gz /data
```

## Configuration Options

- `SCHEMA_SOURCE`: Source of the schema files
  - `local`: Use schema files from mounted volume
  - `github`: Fetch schema from GitHub repository
- `GITHUB_REPO`: GitHub repository containing schema (format: user/repo)
- `GITHUB_TOKEN`: GitHub personal access token for private repositories
- `PORT`: Port to expose the service (default: 3000)
- `PROJECT_NAME`: Name for the deployment (affects volume names)

## Directory Structure for Local Schema

When using `SCHEMA_SOURCE=local`, organize your schema files as follows:

```
schemas/
├── protocol.jsonld
├── activities/
│   ├── activity1.jsonld
│   └── activity2.jsonld
└── items/
    ├── item1.jsonld
    └── item2.jsonld
```

## Examples

Check the `examples/` directory for sample configurations:
- `examples/simple-schema`: Basic single-protocol setup
- `examples/multi-participant`: Setup for multiple participant data collection