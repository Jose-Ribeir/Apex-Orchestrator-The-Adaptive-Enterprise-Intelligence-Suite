import { Router } from "express";
import { asyncHandler } from "../../middleware/asyncHandler";
import { toolsController } from "./controller";

const router = Router();

router.get("/", asyncHandler(toolsController.list));
router.get("/:id", asyncHandler(toolsController.getById));
router.post("/", asyncHandler(toolsController.create));
router.patch("/:id", asyncHandler(toolsController.update));
router.delete("/:id", asyncHandler(toolsController.delete));

export const toolsRoutes = router;
