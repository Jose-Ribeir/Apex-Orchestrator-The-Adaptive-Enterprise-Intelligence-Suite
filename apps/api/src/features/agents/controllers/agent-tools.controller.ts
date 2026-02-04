import { Request, Response } from "express";
import { agentToolService } from "../services/agent-tools.service";
import { paramUuid } from "../../../lib/params";
import { parsePageLimit, paginatedResponse } from "../../../lib/pagination";

export const agentToolsController = {
  listByAgent: async (req: Request, res: Response) => {
    const agentId = paramUuid(req.params.agentId);
    const { page, limit } = parsePageLimit(req);
    const { data, total } = await agentToolService.listByAgent(agentId, {
      page,
      limit,
    });
    res.json(paginatedResponse(data, total, page, limit));
  },

  addTool: async (req: Request, res: Response) => {
    const body = req.body as { toolId: string };
    const result = await agentToolService.addTool(
      paramUuid(req.params.agentId),
      body.toolId,
    );
    res.status(201).json(result);
  },

  removeTool: async (req: Request, res: Response) => {
    await agentToolService.removeTool(
      paramUuid(req.params.agentId),
      paramUuid(req.params.toolId),
    );
    res.status(204).send();
  },
};
