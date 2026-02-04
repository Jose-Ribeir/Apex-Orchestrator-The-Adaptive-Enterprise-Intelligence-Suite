# Tools

CRUD for the tool catalog (e.g. RAG, CoT, Web Search). Tools can be assigned to agents via the agents feature.

## Endpoints

| Method | Path             | Description                    |
| ------ | ---------------- | ------------------------------ |
| GET    | `/api/tools`     | List tools (paginated)         |
| GET    | `/api/tools/:id` | Get tool by id                 |
| POST   | `/api/tools`     | Create tool (body: `{ name }`) |
| PATCH  | `/api/tools/:id` | Update tool (body: `{ name }`) |
| DELETE | `/api/tools/:id` | Soft-delete tool               |

## Dependencies

- **Model:** `Tool` from `src/models`
- **Shared:** `lib/params`, `lib/pagination`, `lib/errors`, `middleware/asyncHandler`
