.PHONY: build up down test lint clean help

help:
	@echo "Available commands:"
	@echo "  make build      - Build Docker images"
	@echo "  make up         - Start the deployment"
	@echo "  make down       - Stop the deployment"
	@echo "  make test       - Run tests"
	@echo "  make lint       - Run linters"
	@echo "  make clean      - Clean up Docker resources"

build:
	docker compose build

up:
	docker compose up -d

down:
	docker compose down

test:
	docker compose -f docker-compose.dev.yml up -d
	docker compose -f docker-compose.dev.yml exec backend python -m pytest tests/
	docker compose -f docker-compose.dev.yml down

lint:
	docker compose -f docker-compose.dev.yml exec backend black .
	docker compose -f docker-compose.dev.yml exec backend isort .

clean:
	docker compose down -v
	docker system prune -f
