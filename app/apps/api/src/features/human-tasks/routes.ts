import { Router } from "express";
import { asyncHandler } from "../../middleware/asyncHandler";
import { humanTasksController } from "./controller";

const router = Router();

router.get("/", asyncHandler(humanTasksController.list));
router.get(
  "/by-query/:modelQueryId",
  asyncHandler(humanTasksController.getByModelQueryId),
);
router.get("/:id", asyncHandler(humanTasksController.getById));
router.post("/", asyncHandler(humanTasksController.create));
router.patch("/:id", asyncHandler(humanTasksController.update));
router.post("/:id/resolve", asyncHandler(humanTasksController.resolve));
router.delete("/:id", asyncHandler(humanTasksController.delete));

export const humanTasksRoutes = router;
