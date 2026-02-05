import { Request, Response } from "express";
import { apiTokensService } from "./service";
import { paramUuid } from "../../lib/params";
import { parsePageLimit, paginatedResponse } from "../../lib/pagination";

export const apiTokensController = {
  /** Create an API token. Plain token returned only in this response. */
  create: async (req: Request, res: Response) => {
    const body = (req.body || {}) as {
      name?: string;
      expiresInDays?: number;
    };
    let expiresAt: Date | null = null;
    if (typeof body.expiresInDays === "number" && body.expiresInDays > 0) {
      const d = new Date();
      d.setDate(d.getDate() + body.expiresInDays);
      expiresAt = d;
    }
    const result = await apiTokensService.createToken(req.user!.id, {
      name: body.name ?? null,
      expiresAt,
    });
    res.status(201).json(result);
  },

  /** List current user's API tokens (no token values), paginated. */
  list: async (req: Request, res: Response) => {
    const { page, limit } = parsePageLimit(req);
    const { data, total } = await apiTokensService.listByUserId(req.user!.id, {
      page,
      limit,
    });
    res.json(paginatedResponse(data, total, page, limit));
  },

  /** Revoke an API token by id. */
  revoke: async (req: Request, res: Response) => {
    await apiTokensService.revoke(paramUuid(req.params.id), req.user!.id);
    res.status(204).send();
  },
};
