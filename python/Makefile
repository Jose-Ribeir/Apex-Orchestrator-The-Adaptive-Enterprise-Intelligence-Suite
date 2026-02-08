# Database migrations (Alembic). Run from python/ with DATABASE_URL set.
# Workers: run with REDIS_URL set. Indexing = documents; prompt = agent prompt generation.

.PHONY: migrate migrate-up migrate-down migrate-redo seed worker worker-prompt

# Apply all pending migrations
migrate: migrate-up

migrate-up:
	alembic upgrade head

# Roll back all migrations (empty DB state)
migrate-down:
	alembic downgrade base

# Redo: roll back to base then apply head (full reset and re-apply)
migrate-redo: migrate-down migrate-up

# Seed default data (Chain-of-Thought, RAG, Straight Model, Web Search). Idempotent.
seed:
	python -c "from app.seed import seed_tools; seed_tools()"

# Document indexing worker (ingest, add-document jobs)
worker:
	python -m app.worker

# Agent prompt generation worker (generate-prompt on agent creation)
worker-prompt:
	python -m app.prompt_worker
