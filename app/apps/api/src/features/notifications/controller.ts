import { Request, Response } from "express";
import { notificationService } from "./service";
import { paramUuid } from "../../lib/params";
import { parsePageLimit, paginatedResponse } from "../../lib/pagination";

export const notificationsController = {
  listByUser: async (req: Request, res: Response) => {
    const unreadOnly = req.query.unread === "true";
    const { page, limit } = parsePageLimit(req);
    const { data, total } = await notificationService.listByUser(
      req.user!.id,
      unreadOnly,
      { page, limit },
    );
    res.json(paginatedResponse(data, total, page, limit));
  },

  getById: async (req: Request, res: Response) => {
    const notification = await notificationService.getById(
      paramUuid(req.params.id),
      req.user!.id,
    );
    res.json(notification);
  },

  markRead: async (req: Request, res: Response) => {
    await notificationService.markRead(paramUuid(req.params.id), req.user!.id);
    res.json({ ok: true });
  },

  markAllRead: async (req: Request, res: Response) => {
    await notificationService.markAllRead(req.user!.id);
    res.json({ ok: true });
  },
};
