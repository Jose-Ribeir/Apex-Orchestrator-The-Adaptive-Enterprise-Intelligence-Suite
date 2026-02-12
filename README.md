git# Apex Orchestrator – The Adaptive Enterprise Intelligence Suite

AI-powered agent dashboard for managing intelligent agents, human-in-the-loop workflows, and performance analytics.

---

## Local Development

### Prerequisites

- **Python 3.11+**, **Node.js 18+**, **pnpm**
- **PostgreSQL** (with pgvector), **Redis**, **MinIO** — see below for two ways to run them

### 0. Start supporting services (Postgres, Redis, MinIO)

Choose one:

**Option A – Docker Compose** (recommended)

```powershell
# PowerShell
cd app
docker compose up -d
```

```bash
# Bash
cd app
docker compose up -d
```

This starts Postgres (5432), Redis (6379), and MinIO (9000/9001). Ensure `app/.env` exists with `POSTGRES_*`, `REDIS_PORT`, `MINIO_*` (or copy from root `.env.example`).

**Option B – Local install**  
Run Postgres, Redis, and MinIO yourself (e.g. installed via package manager).

### 1. Install dependencies

```powershell
# PowerShell - Python backend
cd python
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

```bash
# Bash - Python backend
cd python
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

```powershell
# PowerShell - Frontend
cd app
pnpm install
```

```bash
# Bash - Frontend
cd app
pnpm install
```

### 2. Configure environment

Copy and edit env files:

- **`python/.env`** – copy from `python/.env.dist` (`Copy-Item .env.dist .env`). Set at least:
  - `RAG_PROVIDER=pgvector`, `LLM_PROVIDER=groq`, `STORAGE_PROVIDER=minio`
  - `GROQ_API_KEY`, `DATABASE_URL`, `REDIS_URL`, `MINIO_*`
- **`app/.env`** – copy from root `.env.example`. Set `VITE_API_URL=http://localhost:8000`, `VITE_APP_URL=http://localhost:3000` for local API.

### 3. Run migrations

```powershell
# PowerShell
cd python
.\.venv\Scripts\Activate.ps1
alembic upgrade head
```

```bash
# Bash
cd python && source .venv/bin/activate && alembic upgrade head
```

### 4. Start services (3 terminals)

**Terminal 1 – API**

```powershell
# PowerShell
cd python
.\.venv\Scripts\Activate.ps1
uvicorn main:app --reload
```

```bash
# Bash
cd python && source .venv/bin/activate && uvicorn main:app --reload
```

**Terminal 2 – Worker**

```powershell
# PowerShell
cd python
.\.venv\Scripts\Activate.ps1
python -m app.worker
```

```bash
# Bash
cd python && source .venv/bin/activate && python -m app.worker
```

**Terminal 3 – Frontend**

```powershell
# PowerShell
cd app\apps\web
pnpm dev
```

```bash
# Bash
cd app/apps/web && pnpm dev
```

### 5. Open the app

| Service | URL |
|---------|-----|
| **Web UI** | http://localhost:3000 |
| **API docs** | http://localhost:8000/docs |

---

## Project structure

```
├── app/                # Frontend (React, Vite, pnpm workspace)
│   ├── apps/web/       # Main web app
│   └── packages/       # Shared UI & client
├── python/             # Backend (FastAPI, workers)
│   ├── app/            # Application code
│   ├── alembic/        # Database migrations
│   └── main.py         # API entrypoint
└── .env.example        # Environment template
```

---

## Troubleshooting

| Issue | Action |
|-------|--------|
| API fails with "DATABASE_URL required" | Ensure `DATABASE_URL` and `REDIS_URL` are set in `.env` |
| Frontend can't reach API | Check `VITE_API_URL` matches the API port (default 8000) |
| "GROQ_API_KEY required" | Add a key from https://console.groq.com/keys and set `LLM_PROVIDER=groq` |
| Migrations fail | Run `alembic upgrade head` from `python/` when Postgres is up |
