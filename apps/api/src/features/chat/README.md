# Chat

Streaming chat with an agent: sends message and agent instructions to the Python API and streams the response back. Persists a model query record when the stream completes.

## Endpoints

| Method | Path               | Description                              |
| ------ | ------------------ | ---------------------------------------- |
| POST   | `/api/chat/stream` | Stream response (body: agentId, message) |

## Dependencies

- **Agents feature:** Uses `agentService` and `modelQueryService` from `../agents` to load the agent and save the model query after streaming.
- **Config:** `env.pythonApiUrl` from `src/config/env`
- **Shared:** `lib/params`, `lib/errors`, `middleware/asyncHandler`
