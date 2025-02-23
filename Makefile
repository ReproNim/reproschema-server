.PHONY: build build-verbose up down test lint clean help run stop logs debug

help:
	@echo "Available commands:"
	@echo "  make build      - Build Docker images"
	@echo "  make build-verbose - Build with detailed logs"
	@echo "  make up         - Start the deployment"
	@echo "  make down       - Stop the deployment"
	@echo "  make test       - Run tests"
	@echo "  make lint       - Run linters"
	@echo "  make clean      - Clean up Docker resources"
	@echo "  make run        - Run the container"
	@echo "  make stop       - Stop the container"
	@echo "  make logs       - View container logs"
	@echo "  make debug      - Show config and container state"

build:
	docker compose build

build-verbose:
	docker compose build --no-cache --progress=plain 2>&1 | tee build.log

up:
	docker compose up --force-recreate --remove-orphans

down:
	docker compose down --remove-orphans

test:
	docker compose -f docker-compose.dev.yml up -d
	docker compose -f docker-compose.dev.yml exec backend python -m pytest tests/
	docker compose -f docker-compose.dev.yml down

lint:
	docker compose -f docker-compose.dev.yml exec backend black .
	docker compose -f docker-compose.dev.yml exec backend isort .

clean:
	docker compose down -v --remove-orphans
	docker system prune -f
	docker rm -f reproschema-server

run:
	docker compose up -d

stop:
	docker compose down

logs:
	docker compose logs -f

debug:
	@echo "=== Config Files ==="
	@echo "\n=== Bundled JS Files ==="
	docker compose exec reproschema-server ls -la /usr/share/nginx/html/js/
	@echo "\n=== Config Values in Bundle ==="
	docker compose exec reproschema-server grep -A 10 "githubSrc" /usr/share/nginx/html/js/app.*.js
	@echo "\n=== Environment Variables ==="
	docker compose exec reproschema-server env | grep -E 'SCHEMA|TOKEN|PORT|BACKEND|ASSETS'
	@echo "\n=== Nginx Config ==="
	docker compose exec reproschema-server cat /etc/nginx/conf.d/default.conf | grep -A 5 "location.*${ASSETS_PUBLIC_PATH}"
