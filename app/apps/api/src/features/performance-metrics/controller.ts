import { Request, Response } from "express";
import { performanceMetricService } from "./service";
import { paramUuid } from "../../lib/params";

export const performanceMetricsController = {
  getByModelQueryId: async (req: Request, res: Response) => {
    const metric = await performanceMetricService.getByModelQueryId(
      paramUuid(req.params.modelQueryId),
    );
    res.json(metric);
  },

  getById: async (req: Request, res: Response) => {
    const metric = await performanceMetricService.getById(
      paramUuid(req.params.id),
    );
    res.json(metric);
  },

  create: async (req: Request, res: Response) => {
    const body = req.body as {
      modelQueryId: string;
      tokenUsage: number;
      responseTimeMs?: number;
      efficiencyScore?: number;
      qualityScore?: number;
    };
    const metric = await performanceMetricService.create({
      modelQueryId: body.modelQueryId,
      tokenUsage: body.tokenUsage,
      responseTimeMs: body.responseTimeMs ?? null,
      efficiencyScore: body.efficiencyScore ?? null,
      qualityScore: body.qualityScore ?? null,
    });
    res.status(201).json(metric);
  },

  update: async (req: Request, res: Response) => {
    const body = req.body as {
      tokenUsage?: number;
      responseTimeMs?: number;
      efficiencyScore?: number;
      qualityScore?: number;
    };
    const metric = await performanceMetricService.update(
      paramUuid(req.params.id),
      {
        tokenUsage: body.tokenUsage,
        responseTimeMs: body.responseTimeMs ?? null,
        efficiencyScore: body.efficiencyScore ?? null,
        qualityScore: body.qualityScore ?? null,
      },
    );
    res.json(metric);
  },

  delete: async (req: Request, res: Response) => {
    await performanceMetricService.delete(paramUuid(req.params.id));
    res.status(204).send();
  },
};
