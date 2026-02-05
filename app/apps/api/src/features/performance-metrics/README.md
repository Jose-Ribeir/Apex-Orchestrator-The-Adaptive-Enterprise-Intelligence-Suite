# Performance Metrics

Metrics for model queries (token usage, response time, efficiency/quality scores). One metric per model query.

## Endpoints

| Method | Path                                              | Description                                         |
| ------ | ------------------------------------------------- | --------------------------------------------------- |
| GET    | `/api/performance-metrics/by-query/:modelQueryId` | Get metric by model query id                        |
| GET    | `/api/performance-metrics/:id`                    | Get metric by id                                    |
| POST   | `/api/performance-metrics`                        | Create metric (body: modelQueryId, tokenUsage, ...) |
| PATCH  | `/api/performance-metrics/:id`                    | Update metric                                       |
| DELETE | `/api/performance-metrics/:id`                    | Soft-delete                                         |

## Dependencies

- **Models:** `PerformanceMetric`, `ModelQuery` from `src/models`
- **Shared:** `lib/params`, `lib/errors`, `middleware/asyncHandler`
