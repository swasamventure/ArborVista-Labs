SHELL := /bin/sh

.PHONY: up down logs migrate seed test reset backup

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f database

migrate:
	./scripts/migrate.sh

seed:
	./scripts/seed.sh

test:
	./scripts/test.sh

reset:
	./scripts/reset_local.sh

backup:
	./scripts/backup.sh
