import { Router } from "express";
import { asyncHandler } from "../../middleware/asyncHandler";
import { notificationsController } from "./controller";

const router = Router();

router.get("/", asyncHandler(notificationsController.listByUser));
router.post(
  "/mark-all-read",
  asyncHandler(notificationsController.markAllRead),
);
router.get("/:id", asyncHandler(notificationsController.getById));
router.post("/:id/read", asyncHandler(notificationsController.markRead));

export const notificationsRoutes = router;
