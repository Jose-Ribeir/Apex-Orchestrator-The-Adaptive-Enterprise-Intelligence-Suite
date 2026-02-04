import { Router } from "express";
import { asyncHandler } from "../../middleware/asyncHandler";
import { agentsController } from "./controllers/agents.controller";
import { agentInstructionsController } from "./controllers/instructions.controller";
import { agentToolsController } from "./controllers/agent-tools.controller";
import { modelQueriesController } from "./controllers/model-queries.controller";
import { dailyStatsController } from "./controllers/daily-stats.controller";

const router = Router();

router.get("/", asyncHandler(agentsController.list));
router.post("/", asyncHandler(agentsController.create));

// Nested routes first (so they don't match :id)
router.get(
  "/:agentId/instructions",
  asyncHandler(agentInstructionsController.listByAgent),
);
router.get(
  "/:agentId/instructions/:id",
  asyncHandler(agentInstructionsController.getById),
);
router.post(
  "/:agentId/instructions",
  asyncHandler(agentInstructionsController.create),
);
router.patch(
  "/:agentId/instructions/:id",
  asyncHandler(agentInstructionsController.update),
);
router.delete(
  "/:agentId/instructions/:id",
  asyncHandler(agentInstructionsController.delete),
);

router.get("/:agentId/tools", asyncHandler(agentToolsController.listByAgent));
router.post("/:agentId/tools", asyncHandler(agentToolsController.addTool));
router.delete(
  "/:agentId/tools/:toolId",
  asyncHandler(agentToolsController.removeTool),
);

router.get(
  "/:agentId/queries",
  asyncHandler(modelQueriesController.listByAgent),
);
router.get(
  "/:agentId/queries/:id",
  asyncHandler(modelQueriesController.getById),
);
router.post("/:agentId/queries", asyncHandler(modelQueriesController.create));
router.patch(
  "/:agentId/queries/:id",
  asyncHandler(modelQueriesController.update),
);
router.delete(
  "/:agentId/queries/:id",
  asyncHandler(modelQueriesController.delete),
);

router.get("/:agentId/stats", asyncHandler(dailyStatsController.listByAgent));
router.get(
  "/:agentId/stats/date/:date",
  asyncHandler(dailyStatsController.getByAgentAndDate),
);
router.post("/:agentId/stats", asyncHandler(dailyStatsController.create));
router.patch("/:agentId/stats/:id", asyncHandler(dailyStatsController.update));
router.delete("/:agentId/stats/:id", asyncHandler(dailyStatsController.delete));

// By-id routes last
router.get("/:id", asyncHandler(agentsController.getById));
router.patch("/:id", asyncHandler(agentsController.update));
router.delete("/:id", asyncHandler(agentsController.delete));

export const agentsRoutes = router;
