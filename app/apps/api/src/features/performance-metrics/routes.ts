import { Router } from "express";
import { asyncHandler } from "../../middleware/asyncHandler";
import { performanceMetricsController } from "./controller";

const router = Router();

router.get(
  "/by-query/:modelQueryId",
  asyncHandler(performanceMetricsController.getByModelQueryId),
);
router.get("/:id", asyncHandler(performanceMetricsController.getById));
router.post("/", asyncHandler(performanceMetricsController.create));
router.patch("/:id", asyncHandler(performanceMetricsController.update));
router.delete("/:id", asyncHandler(performanceMetricsController.delete));

export const performanceMetricsRoutes = router;
