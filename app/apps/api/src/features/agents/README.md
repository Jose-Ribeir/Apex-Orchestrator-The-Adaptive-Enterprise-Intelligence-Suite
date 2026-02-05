# Agents

CRUD for agents and nested resources: instructions, tool assignments, model queries, and daily stats. Agents belong to a user and can have ordered instructions and assigned tools (from the tools catalog).

**Layout:** `controllers/` and `services/` subfolders hold the controller and service modules; `routes.ts` wires them at the top of this feature.

## Endpoints

| Method                | Path                                    | Description                                             |
| --------------------- | --------------------------------------- | ------------------------------------------------------- |
| GET                   | `/api/agents`                           | List current user's agents (paginated)                  |
| GET                   | `/api/agents/:id`                       | Get agent by id                                         |
| POST                  | `/api/agents`                           | Create agent (body: name, mode?, instructions?, tools?) |
| PATCH                 | `/api/agents/:id`                       | Update agent                                            |
| DELETE                | `/api/agents/:id`                       | Soft-delete agent                                       |
| GET/POST/PATCH/DELETE | `/api/agents/:agentId/instructions`     | Instructions CRUD                                       |
| GET                   | `/api/agents/:agentId/instructions/:id` | Get instruction by id                                   |
| GET                   | `/api/agents/:agentId/tools`            | List tools assigned to agent                            |
| POST                  | `/api/agents/:agentId/tools`            | Assign tool (body: toolId)                              |
| DELETE                | `/api/agents/:agentId/tools/:toolId`    | Remove tool assignment                                  |
| GET/POST/PATCH/DELETE | `/api/agents/:agentId/queries`          | Model queries CRUD                                      |
| GET                   | `/api/agents/:agentId/queries/:id`      | Get query by id                                         |
| GET                   | `/api/agents/:agentId/stats`            | List daily stats (query: from?, to?)                    |
| GET                   | `/api/agents/:agentId/stats/date/:date` | Get stat by agent and date                              |
| POST/PATCH/DELETE     | `/api/agents/:agentId/stats`            | Create/update/delete daily stat                         |

## Dependencies

- **Models:** `Agent`, `AgentInstruction`, `AgentTool`, `Tool`, `ModelQuery`, `HumanTask`, `PerformanceMetric`, `DailyStat` from `src/models`
- **Shared:** `lib/params`, `lib/pagination`, `lib/errors`, `middleware/asyncHandler`
- **Consumed by:** Chat feature uses `agentService` and `modelQueryService` (exported from this index)
