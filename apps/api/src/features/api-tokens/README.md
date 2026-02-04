# API tokens

Create and manage API tokens for Bearer authentication. Tokens are linked to the authenticated user and can be used with the `Authorization: Bearer <token>` header to access `/api/*` routes.

## Endpoints

- **POST /api/api-tokens** — Create a token (body: `{ name?: string, expiresInDays?: number }`). Returns `{ token, id, name, expiresAt }`; the plain `token` is only returned once.
- **GET /api/api-tokens** — List current user's tokens (paginated; query: `page`, `limit`). Returns `{ data, meta: { pagination } }`; token values are never returned.
- **DELETE /api/api-tokens/:id** — Revoke a token by id.

All endpoints require authentication (session or existing API token).
