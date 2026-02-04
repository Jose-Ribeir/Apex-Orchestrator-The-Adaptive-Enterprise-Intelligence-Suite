import { Request, Response } from "express";
import { toolService } from "./service";
import { paramUuid } from "../../lib/params";
import { parsePageLimit, paginatedResponse } from "../../lib/pagination";

export const toolsController = {
  /** List tools with pagination. */
  list: async (req: Request, res: Response) => {
    const { page, limit } = parsePageLimit(req);
    const { data, total } = await toolService.list({ page, limit });
    res.json(paginatedResponse(data, total, page, limit));
  },

  /** Get a single tool by id. */
  getById: async (req: Request, res: Response) => {
    const tool = await toolService.getById(paramUuid(req.params.id));
    res.json(tool);
  },

  /** Create a new tool. */
  create: async (req: Request, res: Response) => {
    const body = req.body as { name: string };
    const tool = await toolService.create(body.name);
    res.status(201).json(tool);
  },

  /** Update a tool by id. */
  update: async (req: Request, res: Response) => {
    const body = req.body as { name: string };
    const tool = await toolService.update(paramUuid(req.params.id), body.name);
    res.json(tool);
  },

  /** Soft-delete a tool by id. */
  delete: async (req: Request, res: Response) => {
    await toolService.delete(paramUuid(req.params.id));
    res.status(204).send();
  },
};
