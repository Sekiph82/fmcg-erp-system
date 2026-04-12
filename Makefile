.PHONY: dev down logs reset-dev migrate makemigration

ENV_FILE ?= .env.development
DC = docker compose --env-file $(ENV_FILE)

dev:
	$(DC) up -d
	@echo ""
	@echo "Services started (env: $(ENV_FILE)):"
	@$(DC) ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"

down:
	$(DC) down

logs:
	$(DC) logs -f

migrate:
	$(DC) exec backend alembic upgrade head

makemigration:
	$(DC) exec backend alembic revision --autogenerate -m "$(msg)"

reset-dev:
	$(DC) down -v
	$(DC) up -d --build
	@echo ""
	@echo "Environment reset (env: $(ENV_FILE)):"
	@$(DC) ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"
