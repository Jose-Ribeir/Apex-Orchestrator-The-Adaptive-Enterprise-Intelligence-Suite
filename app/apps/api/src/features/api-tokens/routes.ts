import { Router } from "express";
import { asyncHandler } from "../../middleware/asyncHandler";
import { apiTokensController } from "./controller";

const router = Router();

router.post("/", asyncHandler(apiTokensController.create));
router.get("/", asyncHandler(apiTokensController.list));
router.delete("/:id", asyncHandler(apiTokensController.revoke));

export const apiTokensRoutes = router;
