import { Notification } from "../../models";
import { NotFoundError } from "../../lib/errors";
import type { PageLimit } from "../../lib/pagination";

export const notificationService = {
  /**
   * List notifications for a user (paginated), optionally unread only.
   * @param userId - User id
   * @param unreadOnly - If true, filter to isRead false
   * @param pagination - page and limit
   * @returns Paginated list of notifications
   */
  async listByUser(
    userId: string,
    unreadOnly: boolean,
    pagination: PageLimit,
  ): Promise<{ data: Notification[]; total: number }> {
    const where: { userId: string; isRead?: boolean } = { userId };
    if (unreadOnly) where.isRead = false;
    const { page, limit } = pagination;
    const offset = (page - 1) * limit;
    const { count, rows } = await Notification.findAndCountAll({
      where,
      order: [["createdAt", "DESC"]],
      limit,
      offset,
    });
    return { data: rows, total: count };
  },

  /**
   * Get a notification by id, optionally scoped to userId.
   */
  async getById(id: string, userId?: string) {
    const where: { id: string; userId?: string } = { id };
    if (userId) where.userId = userId;
    const notification = await Notification.findOne({ where });
    if (!notification) throw new NotFoundError("Notification", id);
    return notification;
  },

  /**
   * Mark a notification as read.
   */
  async markRead(id: string, userId: string) {
    const notification = await this.getById(id, userId);
    await notification.update({ isRead: true });
    return notification;
  },

  /**
   * Mark all notifications for a user as read.
   */
  async markAllRead(userId: string) {
    await Notification.update(
      { isRead: true },
      { where: { userId, isRead: false } },
    );
    return { ok: true };
  },
};
