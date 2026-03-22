.PHONY: dev test lint format

dev:
	docker compose up

test:
	cd apps/web && npm test
	cd apps/api && pytest

lint:
	cd apps/web && npm run lint

format:
	cd apps/web && npm run format
