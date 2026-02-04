import { Request, Response } from "express";
import { humanTaskService } from "./service";
import { paramUuid } from "../../lib/params";
import { parsePageLimit, paginatedResponse } from "../../lib/pagination";

export const humanTasksController = {
  list: async (req: Request, res: Response) => {
    const pendingOnly = req.query.pending === "true";
    const { page, limit } = parsePageLimit(req);
    const { data, total } = await humanTaskService.list(pendingOnly, {
      page,
      limit,
    });
    res.json(paginatedResponse(data, total, page, limit));
  },

  getById: async (req: Request, res: Response) => {
    const task = await humanTaskService.getById(paramUuid(req.params.id));
    res.json(task);
  },

  getByModelQueryId: async (req: Request, res: Response) => {
    const task = await humanTaskService.getByModelQueryId(
      paramUuid(req.params.modelQueryId),
    );
    res.json(task);
  },

  create: async (req: Request, res: Response) => {
    const body = req.body as {
      modelQueryId: string;
      reason: string;
      retrievedData?: string;
      modelMessage: string;
      status?: string;
    };
    const task = await humanTaskService.create({
      modelQueryId: body.modelQueryId,
      reason: body.reason,
      retrievedData: body.retrievedData ?? null,
      modelMessage: body.modelMessage,
      status: body.status as "PENDING" | "RESOLVED" | undefined,
    });
    res.status(201).json(task);
  },

  update: async (req: Request, res: Response) => {
    const body = req.body as {
      reason?: string;
      retrievedData?: string;
      modelMessage?: string;
      status?: string;
    };
    const task = await humanTaskService.update(paramUuid(req.params.id), {
      reason: body.reason,
      retrievedData: body.retrievedData ?? null,
      modelMessage: body.modelMessage,
      status: body.status as "PENDING" | "RESOLVED" | undefined,
    });
    res.json(task);
  },

  resolve: async (req: Request, res: Response) => {
    const task = await humanTaskService.resolve(paramUuid(req.params.id));
    res.json(task);
  },

  delete: async (req: Request, res: Response) => {
    await humanTaskService.delete(paramUuid(req.params.id));
    res.status(204).send();
  },
};
