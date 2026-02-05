# Human Tasks

Human-in-the-loop tasks linked to model queries. Used when a query requires human review or input (e.g. RAG retrieval needs verification).

## Endpoints

| Method | Path                                      | Description                                                 |
| ------ | ----------------------------------------- | ----------------------------------------------------------- |
| GET    | `/api/human-tasks`                        | List tasks (query: `pending=true` for pending only)         |
| GET    | `/api/human-tasks/by-query/:modelQueryId` | Get task by model query id                                  |
| GET    | `/api/human-tasks/:id`                    | Get task by id                                              |
| POST   | `/api/human-tasks`                        | Create task (body: modelQueryId, reason, modelMessage, ...) |
| PATCH  | `/api/human-tasks/:id`                    | Update task                                                 |
| POST   | `/api/human-tasks/:id/resolve`            | Mark as resolved                                            |
| DELETE | `/api/human-tasks/:id`                    | Soft-delete                                                 |

## Dependencies

- **Models:** `HumanTask`, `ModelQuery` from `src/models`
- **Shared:** `lib/params`, `lib/pagination`, `lib/errors`, `middleware/asyncHandler`
