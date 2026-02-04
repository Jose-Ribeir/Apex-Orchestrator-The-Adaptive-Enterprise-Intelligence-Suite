import { Request, Response } from "express";
import { agentInstructionService } from "../services/instructions.service";
import { paramUuid } from "../../../lib/params";
import { parsePageLimit, paginatedResponse } from "../../../lib/pagination";

export const agentInstructionsController = {
  listByAgent: async (req: Request, res: Response) => {
    const agentId = paramUuid(req.params.agentId);
    const { page, limit } = parsePageLimit(req);
    const { data, total } = await agentInstructionService.listByAgent(agentId, {
      page,
      limit,
    });
    res.json(paginatedResponse(data, total, page, limit));
  },

  getById: async (req: Request, res: Response) => {
    const instruction = await agentInstructionService.getById(
      paramUuid(req.params.id),
      paramUuid(req.params.agentId),
    );
    res.json(instruction);
  },

  create: async (req: Request, res: Response) => {
    const body = req.body as { content: string; order?: number };
    const instruction = await agentInstructionService.create({
      agentId: paramUuid(req.params.agentId),
      content: body.content,
      order: body.order ?? 0,
    });
    res.status(201).json(instruction);
  },

  update: async (req: Request, res: Response) => {
    const body = req.body as { content?: string; order?: number };
    const instruction = await agentInstructionService.update(
      paramUuid(req.params.id),
      paramUuid(req.params.agentId),
      { content: body.content, order: body.order },
    );
    res.json(instruction);
  },

  delete: async (req: Request, res: Response) => {
    await agentInstructionService.delete(
      paramUuid(req.params.id),
      paramUuid(req.params.agentId),
    );
    res.status(204).send();
  },
};
