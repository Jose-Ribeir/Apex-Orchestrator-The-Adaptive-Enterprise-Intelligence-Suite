import { Request, Response } from "express";
import { modelQueryService } from "../services/model-queries.service";
import { paramUuid } from "../../../lib/params";
import { parsePageLimit, paginatedResponse } from "../../../lib/pagination";

export const modelQueriesController = {
  listByAgent: async (req: Request, res: Response) => {
    const agentId = paramUuid(req.params.agentId);
    const { page, limit } = parsePageLimit(req);
    const { data, total } = await modelQueryService.listByAgent(agentId, {
      page,
      limit,
    });
    res.json(paginatedResponse(data, total, page, limit));
  },

  getById: async (req: Request, res: Response) => {
    const query = await modelQueryService.getById(
      paramUuid(req.params.id),
      paramUuid(req.params.agentId),
    );
    res.json(query);
  },

  create: async (req: Request, res: Response) => {
    const body = req.body as {
      userQuery: string;
      modelResponse?: string;
      methodUsed?: string;
    };
    const modelQuery = await modelQueryService.create({
      agentId: paramUuid(req.params.agentId),
      userQuery: body.userQuery,
      modelResponse: body.modelResponse ?? null,
      methodUsed:
        (body.methodUsed as "PERFORMANCE" | "EFFICIENCY") || "EFFICIENCY",
    });
    res.status(201).json(modelQuery);
  },

  update: async (req: Request, res: Response) => {
    const body = req.body as { modelResponse?: string };
    const modelQuery = await modelQueryService.update(
      paramUuid(req.params.id),
      paramUuid(req.params.agentId),
      { modelResponse: body.modelResponse ?? null },
    );
    res.json(modelQuery);
  },

  delete: async (req: Request, res: Response) => {
    await modelQueryService.delete(
      paramUuid(req.params.id),
      paramUuid(req.params.agentId),
    );
    res.status(204).send();
  },
};
