import { ModelQuery, HumanTask, PerformanceMetric } from "../../../models";
import { NotFoundError, ValidationError } from "../../../lib/errors";
import type { QueryMethod } from "../../../models/ModelQuery";
import type { PageLimit } from "../../../lib/pagination";

export interface CreateModelQueryInput {
  agentId: string;
  userQuery: string;
  modelResponse?: string | null;
  methodUsed: QueryMethod;
}

export interface UpdateModelQueryInput {
  modelResponse?: string | null;
}

export const modelQueryService = {
  /**
   * List model queries for an agent (paginated, newest first).
   */
  async listByAgent(
    agentId: string,
    pagination: PageLimit,
  ): Promise<{ data: ModelQuery[]; total: number }> {
    const { page, limit } = pagination;
    const offset = (page - 1) * limit;
    const total = await ModelQuery.count({ where: { agentId } });
    const rows = await ModelQuery.findAll({
      where: { agentId },
      order: [["createdAt", "DESC"]],
      limit,
      offset,
      include: [
        { model: HumanTask, as: "humanTask", required: false },
        { model: PerformanceMetric, as: "metrics", required: false },
      ],
    });
    return { data: rows, total };
  },

  /**
   * Get a single model query by id, optionally scoped to agentId.
   */
  async getById(id: string, agentId?: string) {
    const where: { id: string; agentId?: string } = { id };
    if (agentId) where.agentId = agentId;
    const query = await ModelQuery.findOne({
      where,
      include: [
        { model: HumanTask, as: "humanTask", required: false },
        { model: PerformanceMetric, as: "metrics", required: false },
      ],
    });
    if (!query) throw new NotFoundError("ModelQuery", id);
    return query;
  },

  /**
   * Create a model query record (e.g. after a chat completion).
   */
  async create(input: CreateModelQueryInput) {
    if (!input.userQuery?.trim())
      throw new ValidationError("userQuery is required");
    return ModelQuery.create({
      agentId: input.agentId,
      userQuery: input.userQuery.trim(),
      modelResponse: input.modelResponse ?? null,
      methodUsed: input.methodUsed ?? "EFFICIENCY",
    });
  },

  /**
   * Update a model query (e.g. modelResponse).
   */
  async update(id: string, agentId: string, input: UpdateModelQueryInput) {
    const query = await this.getById(id, agentId);
    if (input.modelResponse !== undefined)
      query.modelResponse = input.modelResponse;
    await query.save();
    return this.getById(query.id);
  },

  /**
   * Soft-delete a model query.
   */
  async delete(id: string, agentId: string) {
    const query = await this.getById(id, agentId);
    await query.update({ isDeleted: true, deletedAt: new Date() });
    return { ok: true };
  },
};
