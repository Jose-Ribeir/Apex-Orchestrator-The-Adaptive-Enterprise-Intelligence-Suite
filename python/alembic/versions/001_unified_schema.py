"""Unified schema: auth, api_tokens, agents (with metadata), tools, agent_documents, model_queries, human_tasks.

Revision ID: 001_unified
Revises: 001_init
Create Date: 2026-02-07

Run from clean state: alembic upgrade head
Redo (reset and re-apply): alembic downgrade base && alembic upgrade head
"""

from collections.abc import Sequence

from alembic import op

revision: str = "001_unified"
down_revision: str | None = "001_init"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ----- Auth (Better Auth / FastAPI Users compatible) -----
    op.execute("""
        CREATE TABLE IF NOT EXISTS "user" (
            "id" TEXT PRIMARY KEY,
            "name" TEXT NOT NULL,
            "email" TEXT NOT NULL,
            "emailVerified" BOOLEAN NOT NULL DEFAULT false,
            "image" TEXT,
            "createdAt" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            "updatedAt" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS "session" (
            "id" TEXT PRIMARY KEY,
            "userId" TEXT NOT NULL REFERENCES "user"("id") ON DELETE CASCADE,
            "token" TEXT NOT NULL UNIQUE,
            "expiresAt" TIMESTAMP WITH TIME ZONE NOT NULL,
            "ipAddress" TEXT,
            "userAgent" TEXT,
            "createdAt" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            "updatedAt" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS "account" (
            "id" TEXT PRIMARY KEY,
            "userId" TEXT NOT NULL REFERENCES "user"("id") ON DELETE CASCADE,
            "accountId" TEXT NOT NULL,
            "providerId" TEXT NOT NULL,
            "accessToken" TEXT,
            "refreshToken" TEXT,
            "accessTokenExpiresAt" TIMESTAMP WITH TIME ZONE,
            "refreshTokenExpiresAt" TIMESTAMP WITH TIME ZONE,
            "scope" TEXT,
            "idToken" TEXT,
            "password" TEXT,
            "createdAt" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            "updatedAt" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS "verification" (
            "id" TEXT PRIMARY KEY,
            "identifier" TEXT NOT NULL,
            "value" TEXT NOT NULL,
            "expiresAt" TIMESTAMP WITH TIME ZONE NOT NULL,
            "createdAt" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            "updatedAt" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        )
    """)
    op.execute('CREATE INDEX IF NOT EXISTS "session_userId_idx" ON "session"("userId")')
    op.execute('CREATE INDEX IF NOT EXISTS "account_userId_idx" ON "account"("userId")')

    op.execute('ALTER TABLE "user" ADD COLUMN IF NOT EXISTS "hashed_password" TEXT')
    op.execute('ALTER TABLE "user" ADD COLUMN IF NOT EXISTS "is_active" BOOLEAN NOT NULL DEFAULT true')
    op.execute('ALTER TABLE "user" ADD COLUMN IF NOT EXISTS "is_superuser" BOOLEAN NOT NULL DEFAULT false')

    # ----- API tokens -----
    op.execute("""
        CREATE TABLE IF NOT EXISTS api_tokens (
            id UUID NOT NULL PRIMARY KEY,
            user_id TEXT NOT NULL,
            token_hash TEXT NOT NULL,
            name TEXT,
            last_used_at TIMESTAMP WITH TIME ZONE,
            expires_at TIMESTAMP WITH TIME ZONE,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_api_tokens_token_hash ON api_tokens (token_hash)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_api_tokens_user_id ON api_tokens (user_id)")
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'api_tokens_user_id_fkey') THEN
                ALTER TABLE api_tokens ADD CONSTRAINT api_tokens_user_id_fkey
                FOREIGN KEY (user_id) REFERENCES "user"(id) ON DELETE CASCADE;
            END IF;
        END $$
    """)

    # ----- Tools -----
    op.execute("""
        CREATE TABLE IF NOT EXISTS tools (
            id UUID NOT NULL PRIMARY KEY,
            name VARCHAR NOT NULL,
            is_deleted BOOLEAN NOT NULL DEFAULT false,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            deleted_at TIMESTAMP WITH TIME ZONE
        )
    """)
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_tools_name ON tools (name)")

    # ----- Agents (with metadata) -----
    op.execute("""
        CREATE TABLE IF NOT EXISTS agents (
            id UUID NOT NULL PRIMARY KEY,
            user_id VARCHAR NOT NULL,
            name VARCHAR NOT NULL,
            mode VARCHAR NOT NULL,
            prompt TEXT,
            is_deleted BOOLEAN NOT NULL DEFAULT false,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            deleted_at TIMESTAMP WITH TIME ZONE,
            metadata JSONB
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_agents_user_id ON agents (user_id)")
    # Add metadata column if table already existed without it (e.g. from an older migration)
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = 'agents' AND column_name = 'metadata'
            ) THEN
                ALTER TABLE agents ADD COLUMN metadata JSONB;
            END IF;
        END $$
    """)
    op.execute("""
        UPDATE agents
        SET metadata = '{"status": {"indexing": "completed"}}'::jsonb
        WHERE metadata IS NULL
    """)

    # ----- Agent instructions -----
    op.execute("""
        CREATE TABLE IF NOT EXISTS agent_instructions (
            id UUID NOT NULL PRIMARY KEY,
            agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
            content TEXT NOT NULL,
            "order" INTEGER NOT NULL,
            is_deleted BOOLEAN NOT NULL DEFAULT false,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            deleted_at TIMESTAMP WITH TIME ZONE
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_agent_instructions_agent_id ON agent_instructions (agent_id)")

    # ----- Agent tools (join table) -----
    op.execute("""
        CREATE TABLE IF NOT EXISTS agent_tools (
            agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
            tool_id UUID NOT NULL REFERENCES tools(id) ON DELETE CASCADE,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            PRIMARY KEY (agent_id, tool_id)
        )
    """)

    # ----- Agent documents (RAG document metadata) -----
    op.execute("""
        CREATE TABLE IF NOT EXISTS agent_documents (
            id UUID NOT NULL PRIMARY KEY,
            agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
            document_id VARCHAR(512) NOT NULL,
            name VARCHAR(512) NOT NULL,
            source_filename VARCHAR(512),
            content_preview TEXT,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_agent_documents_agent_id ON agent_documents (agent_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_agent_documents_document_id ON agent_documents (document_id)")
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_agent_documents_agent_document_id "
        "ON agent_documents (agent_id, document_id)"
    )

    # ----- Model queries -----
    op.execute("""
        CREATE TABLE IF NOT EXISTS model_queries (
            id UUID NOT NULL PRIMARY KEY,
            agent_id UUID NOT NULL REFERENCES agents(id) ON UPDATE CASCADE ON DELETE RESTRICT,
            user_query TEXT NOT NULL,
            model_response TEXT,
            method_used VARCHAR NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            is_deleted BOOLEAN NOT NULL DEFAULT false,
            deleted_at TIMESTAMP WITH TIME ZONE
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_model_queries_agent_id ON model_queries (agent_id)")

    # ----- Human tasks -----
    op.execute("""
        CREATE TABLE IF NOT EXISTS human_tasks (
            id UUID NOT NULL PRIMARY KEY,
            model_query_id UUID NOT NULL REFERENCES model_queries(id) ON UPDATE CASCADE ON DELETE CASCADE,
            reason TEXT NOT NULL,
            retrieved_data TEXT,
            model_message TEXT NOT NULL,
            status VARCHAR NOT NULL DEFAULT 'PENDING',
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            is_deleted BOOLEAN NOT NULL DEFAULT false,
            deleted_at TIMESTAMP WITH TIME ZONE
        )
    """)
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_human_tasks_model_query_id ON human_tasks (model_query_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS human_tasks")
    op.execute("DROP TABLE IF EXISTS model_queries")
    op.execute("DROP TABLE IF EXISTS agent_documents")
    op.execute("DROP TABLE IF EXISTS agent_tools")
    op.execute("DROP TABLE IF EXISTS agent_instructions")
    op.execute("DROP TABLE IF EXISTS agents")
    op.execute("DROP TABLE IF EXISTS tools")
    op.execute("DROP TABLE IF EXISTS api_tokens")
    op.execute('DROP TABLE IF EXISTS "verification"')
    op.execute('DROP TABLE IF EXISTS "account"')
    op.execute('DROP TABLE IF EXISTS "session"')
    op.execute('DROP TABLE IF EXISTS "user"')
