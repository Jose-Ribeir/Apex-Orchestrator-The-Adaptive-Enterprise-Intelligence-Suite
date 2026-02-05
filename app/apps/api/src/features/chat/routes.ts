import { Router } from "express";
import { asyncHandler } from "../../middleware/asyncHandler";
import { chatController } from "./controller";

const router = Router();

router.post("/stream", asyncHandler(chatController.stream));

export const chatRoutes = router;
