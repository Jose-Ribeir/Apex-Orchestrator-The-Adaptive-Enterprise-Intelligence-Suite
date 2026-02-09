# Database migrations (Alembic). Run from python/ with DATABASE_URL set.
# Worker: run with REDIS_URL set. Handles indexing (documents) and prompt generation queues.

.PHONY: migrate migrate-up migrate-down migrate-redo seed worker

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

# Single worker for indexing (ingest, add-document) and prompt generation queues
worker:
	python -m app.worker
