import { HumanTask, ModelQuery } from "../../models";
import { NotFoundError, ValidationError } from "../../lib/errors";
import type { HumanTaskStatus } from "../../models/HumanTask";
import type { PageLimit } from "../../lib/pagination";

export interface CreateHumanTaskInput {
  modelQueryId: string;
  reason: string;
  retrievedData?: string | null;
  modelMessage: string;
  status?: HumanTaskStatus;
}

export interface UpdateHumanTaskInput {
  reason?: string;
  retrievedData?: string | null;
  modelMessage?: string;
  status?: HumanTaskStatus;
}

export const humanTaskService = {
  /**
   * List human tasks (optionally pending only), paginated.
   * @param pendingOnly - If true, filter to status PENDING
   * @param pagination - page and limit
   * @returns Paginated list of human tasks with modelQuery included
   */
  async list(
    pendingOnly: boolean,
    pagination: PageLimit,
  ): Promise<{ data: HumanTask[]; total: number }> {
    const where: { status?: HumanTaskStatus } = {};
    if (pendingOnly) where.status = "PENDING";
    const { page, limit } = pagination;
    const offset = (page - 1) * limit;
    const total = await HumanTask.count({ where });
    const rows = await HumanTask.findAll({
      where,
      order: [["createdAt", "DESC"]],
      limit,
      offset,
      include: [{ model: ModelQuery, as: "modelQuery" }],
    });
    return { data: rows, total };
  },

  /**
   * Get a human task by id.
   */
  async getById(id: string) {
    const task = await HumanTask.findOne({
      where: { id },
      include: [{ model: ModelQuery, as: "modelQuery" }],
    });
    if (!task) throw new NotFoundError("HumanTask", id);
    return task;
  },

  /**
   * Get a human task by model query id (1:1).
   */
  async getByModelQueryId(modelQueryId: string) {
    const task = await HumanTask.findOne({
      where: { modelQueryId },
      include: [{ model: ModelQuery, as: "modelQuery" }],
    });
    if (!task) throw new NotFoundError("HumanTask");
    return task;
  },

  /**
   * Create a human-in-the-loop task for a model query.
   * @param input - modelQueryId, reason, modelMessage (required); status, retrievedData optional
   * @throws ValidationError if reason or modelMessage missing; NotFoundError if model query not found
   */
  async create(input: CreateHumanTaskInput) {
    if (!input.reason?.trim()) throw new ValidationError("reason is required");
    if (!input.modelMessage?.trim())
      throw new ValidationError("modelMessage is required");
    const modelQuery = await ModelQuery.findByPk(input.modelQueryId);
    if (!modelQuery) throw new NotFoundError("ModelQuery", input.modelQueryId);
    return HumanTask.create({
      modelQueryId: input.modelQueryId,
      reason: input.reason.trim(),
      retrievedData: input.retrievedData ?? null,
      modelMessage: input.modelMessage.trim(),
      status: input.status ?? "PENDING",
    });
  },

  /**
   * Update a human task (reason, retrievedData, modelMessage, status).
   */
  async update(id: string, input: UpdateHumanTaskInput) {
    const task = await this.getById(id);
    if (input.reason !== undefined) task.reason = input.reason.trim();
    if (input.retrievedData !== undefined)
      task.retrievedData = input.retrievedData;
    if (input.modelMessage !== undefined)
      task.modelMessage = input.modelMessage.trim();
    if (input.status !== undefined) task.status = input.status;
    await task.save();
    return this.getById(id);
  },

  /**
   * Mark a human task as resolved.
   */
  async resolve(id: string) {
    return this.update(id, { status: "RESOLVED" });
  },

  /**
   * Soft-delete a human task.
   */
  async delete(id: string) {
    const task = await this.getById(id);
    await task.update({ isDeleted: true, deletedAt: new Date() });
    return { ok: true };
  },
};
