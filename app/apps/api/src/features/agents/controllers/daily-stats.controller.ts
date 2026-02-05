import { Request, Response } from "express";
import { dailyStatService } from "../services/daily-stats.service";
import { paramId, paramUuid } from "../../../lib/params";
import { parsePageLimit, paginatedResponse } from "../../../lib/pagination";

export const dailyStatsController = {
  listByAgent: async (req: Request, res: Response) => {
    const agentId = paramUuid(req.params.agentId);
    const from = req.query.from as string | undefined;
    const to = req.query.to as string | undefined;
    const { page, limit } = parsePageLimit(req);
    const { data, total } = await dailyStatService.listByAgent(
      agentId,
      { page, limit },
      from,
      to,
    );
    res.json(paginatedResponse(data, total, page, limit));
  },

  getById: async (req: Request, res: Response) => {
    const stat = await dailyStatService.getById(paramUuid(req.params.id));
    res.json(stat);
  },

  getByAgentAndDate: async (req: Request, res: Response) => {
    const stat = await dailyStatService.getByAgentAndDate(
      paramUuid(req.params.agentId),
      paramId(req.params.date),
    );
    res.json(stat);
  },

  create: async (req: Request, res: Response) => {
    const body = req.body as {
      date: string;
      totalQueries: number;
      totalTokens: number;
      avgEfficiency?: number;
      avgQuality?: number;
    };
    const stat = await dailyStatService.create({
      agentId: paramUuid(req.params.agentId),
      date: body.date,
      totalQueries: body.totalQueries,
      totalTokens: body.totalTokens,
      avgEfficiency: body.avgEfficiency ?? null,
      avgQuality: body.avgQuality ?? null,
    });
    res.status(201).json(stat);
  },

  update: async (req: Request, res: Response) => {
    const body = req.body as {
      totalQueries?: number;
      totalTokens?: number;
      avgEfficiency?: number;
      avgQuality?: number;
    };
    const stat = await dailyStatService.update(paramUuid(req.params.id), {
      totalQueries: body.totalQueries,
      totalTokens: body.totalTokens,
      avgEfficiency: body.avgEfficiency ?? null,
      avgQuality: body.avgQuality ?? null,
    });
    res.json(stat);
  },

  delete: async (req: Request, res: Response) => {
    await dailyStatService.delete(paramUuid(req.params.id));
    res.status(204).send();
  },
};
