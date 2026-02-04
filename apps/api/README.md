# AI Router API

Node.js backend with Express, Sequelize (PostgreSQL), Scalar API docs, and Better Auth.

- **`/api/*`** — main API (agents, tools, chat, etc.)
- **`/auth/*`** — Better Auth (email/password, sessions, etc.)

## Architecture

The API is organized by **feature** (domain). Each feature lives under `src/features/` with its routes, controller(s), and service(s) co-located in one folder.

| Feature             | Path                                | Description                                                              |
| ------------------- | ----------------------------------- | ------------------------------------------------------------------------ |
| Tools               | `src/features/tools/`               | Tool catalog CRUD                                                        |
| Agents              | `src/features/agents/`              | Agents CRUD + instructions, tool assignments, model queries, daily stats |
| Human tasks         | `src/features/human-tasks/`         | Human-in-the-loop tasks linked to model queries                          |
| Performance metrics | `src/features/performance-metrics/` | Metrics per model query                                                  |
| Notifications       | `src/features/notifications/`       | User notifications (list, mark read)                                     |
| Chat                | `src/features/chat/`                | Streaming chat (uses agents feature for agent + model query)             |

**Shared code** (used by features):

- `src/lib/` — auth, errors, pagination, params
- `src/middleware/` — asyncHandler, errorHandler, requireAuth
- `src/config/` — env, database
- `src/models/` — Sequelize models and associations
- `src/types/` — Express augmentation (e.g. `req.user`)
- `src/openapi/` — OpenAPI spec for docs

Each feature folder includes a `README.md` with purpose, endpoints, and dependencies.

## Setup

```bash
# From repo root
pnpm install
```

## Database

- **Migrations** (from `apps/api`): `pnpm db:migrate`
- **Default URL**: `postgresql://postgres:postgres@localhost:5432/ai_router`

### Seeding

From `apps/api` (or repo root with `pnpm --filter @ai-router/api <script>`):

```bash
# 1. Run migrations
pnpm db:migrate

# 2. Seed tools + default admin user (INSERTs; bcrypt hash matches auth config)
pnpm db:seed
```

## Run

```bash
# From repo root
pnpm --filter @ai-router/api dev
# Or from apps/api
pnpm dev
```

- API: http://localhost:4000/api
- Auth (Better Auth): http://localhost:4000/auth
- Scalar docs: http://localhost:4000/docs
- OpenAPI JSON: http://localhost:4000/openapi.json

## Docker

From repo root (no `.env` required; defaults work):

```bash
docker compose up -d
```

Override with a `.env` file: `docker compose --env-file .env up -d`

- Postgres: port 5432 (default)
- API: port 4000 (default). Migrations run on startup.
