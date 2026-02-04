import { PerformanceMetric, ModelQuery } from "../../models";
import { NotFoundError, ValidationError } from "../../lib/errors";

export interface CreatePerformanceMetricInput {
  modelQueryId: string;
  tokenUsage: number;
  responseTimeMs?: number | null;
  efficiencyScore?: number | null;
  qualityScore?: number | null;
}

export interface UpdatePerformanceMetricInput {
  tokenUsage?: number;
  responseTimeMs?: number | null;
  efficiencyScore?: number | null;
  qualityScore?: number | null;
}

export const performanceMetricService = {
  /**
   * Get the performance metric for a model query (1:1).
   * @param modelQueryId - Model query UUID
   * @throws NotFoundError if no metric for that query
   */
  async getByModelQueryId(modelQueryId: string) {
    const metric = await PerformanceMetric.findOne({
      where: { modelQueryId },
      include: [{ model: ModelQuery, as: "modelQuery" }],
    });
    if (!metric) throw new NotFoundError("PerformanceMetric");
    return metric;
  },

  /**
   * Get a performance metric by id.
   */
  async getById(id: string) {
    const metric = await PerformanceMetric.findByPk(id, {
      include: [{ model: ModelQuery, as: "modelQuery" }],
    });
    if (!metric) throw new NotFoundError("PerformanceMetric", id);
    return metric;
  },

  /**
   * Create a performance metric for a model query.
   * @param input - modelQueryId, tokenUsage (required); responseTimeMs, efficiencyScore, qualityScore optional
   * @throws ValidationError if tokenUsage missing or negative; NotFoundError if model query not found
   */
  async create(input: CreatePerformanceMetricInput) {
    if (input.tokenUsage == null || input.tokenUsage < 0)
      throw new ValidationError("tokenUsage is required and must be >= 0");
    const modelQuery = await ModelQuery.findByPk(input.modelQueryId);
    if (!modelQuery) throw new NotFoundError("ModelQuery", input.modelQueryId);
    return PerformanceMetric.create({
      modelQueryId: input.modelQueryId,
      tokenUsage: input.tokenUsage,
      responseTimeMs: input.responseTimeMs ?? null,
      efficiencyScore: input.efficiencyScore ?? null,
      qualityScore: input.qualityScore ?? null,
    });
  },

  /**
   * Update a performance metric.
   */
  async update(id: string, input: UpdatePerformanceMetricInput) {
    const metric = await this.getById(id);
    if (input.tokenUsage !== undefined) metric.tokenUsage = input.tokenUsage;
    if (input.responseTimeMs !== undefined)
      metric.responseTimeMs = input.responseTimeMs;
    if (input.efficiencyScore !== undefined)
      metric.efficiencyScore = input.efficiencyScore;
    if (input.qualityScore !== undefined)
      metric.qualityScore = input.qualityScore;
    await metric.save();
    return this.getById(id);
  },

  /**
   * Soft-delete a performance metric.
   */
  async delete(id: string) {
    const metric = await this.getById(id);
    await metric.update({ isDeleted: true, deletedAt: new Date() });
    return { ok: true };
  },
};
