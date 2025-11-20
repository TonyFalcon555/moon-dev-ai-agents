.PHONY: up down logs test clean deploy-prod help

help:
	@echo "Falcon Finance AI Agents - Make Commands"
	@echo "----------------------------------"
	@echo "make up          : Start all services in development mode"
	@echo "make down        : Stop all services"
	@echo "make logs        : View logs for all services"
	@echo "make test        : Run all unit tests"
	@echo "make clean       : Remove pycache and temporary files"
	@echo "make deploy-prod : Start all services in production mode"

up:
	docker-compose up -d --build

down:
	docker-compose down

logs:
	docker-compose logs -f

test:
	./venv/bin/python -m pytest tests/ -v

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +

deploy-prod:
	docker-compose -f docker-compose.prod.yml up -d --build
