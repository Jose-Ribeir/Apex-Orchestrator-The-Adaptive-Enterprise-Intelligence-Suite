import { Op } from "sequelize";
import { DailyStat, Agent } from "../../../models";
import { NotFoundError, ValidationError } from "../../../lib/errors";
import type { PageLimit } from "../../../lib/pagination";

export interface CreateDailyStatInput {
  agentId: string;
  date: string; // YYYY-MM-DD
  totalQueries: number;
  totalTokens: number;
  avgEfficiency?: number | null;
  avgQuality?: number | null;
}

export interface UpdateDailyStatInput {
  totalQueries?: number;
  totalTokens?: number;
  avgEfficiency?: number | null;
  avgQuality?: number | null;
}

export const dailyStatService = {
  /**
   * List daily stats for an agent (paginated), optional date range.
   */
  async listByAgent(
    agentId: string,
    pagination: PageLimit,
    from?: string,
    to?: string,
  ): Promise<{ data: DailyStat[]; total: number }> {
    const where: {
      agentId: string;
      date?: { [Op.gte]?: string; [Op.lte]?: string };
    } = { agentId };
    if (from || to) {
      where.date = {};
      if (from) where.date[Op.gte] = from;
      if (to) where.date[Op.lte] = to;
    }
    const { page, limit } = pagination;
    const offset = (page - 1) * limit;
    const total = await DailyStat.count({ where });
    const rows = await DailyStat.findAll({
      where,
      order: [["date", "DESC"]],
      limit,
      offset,
      include: [{ model: Agent, as: "agent" }],
    });
    return { data: rows, total };
  },

  /**
   * Get a daily stat by id.
   */
  async getById(id: string) {
    const stat = await DailyStat.findByPk(id, {
      include: [{ model: Agent, as: "agent" }],
    });
    if (!stat) throw new NotFoundError("DailyStat", id);
    return stat;
  },

  /**
   * Get a daily stat by agent and date.
   */
  async getByAgentAndDate(agentId: string, date: string) {
    const stat = await DailyStat.findOne({
      where: { agentId, date },
      include: [{ model: Agent, as: "agent" }],
    });
    if (!stat) throw new NotFoundError("DailyStat");
    return stat;
  },

  /**
   * Create or update a daily stat for an agent/date.
   */
  async create(input: CreateDailyStatInput) {
    if (!input.date) throw new ValidationError("date is required");
    if (input.totalQueries == null || input.totalQueries < 0)
      throw new ValidationError("totalQueries is required and must be >= 0");
    if (input.totalTokens == null || input.totalTokens < 0)
      throw new ValidationError("totalTokens is required and must be >= 0");
    const agent = await Agent.findByPk(input.agentId);
    if (!agent) throw new NotFoundError("Agent", input.agentId);
    const [stat, created] = await DailyStat.findOrCreate({
      where: { agentId: input.agentId, date: new Date(input.date) },
      defaults: {
        agentId: input.agentId,
        date: new Date(input.date),
        totalQueries: input.totalQueries,
        totalTokens: input.totalTokens,
        avgEfficiency: input.avgEfficiency ?? null,
        avgQuality: input.avgQuality ?? null,
      },
    });
    if (!created) {
      await stat.update({
        totalQueries: input.totalQueries,
        totalTokens: input.totalTokens,
        avgEfficiency: input.avgEfficiency ?? null,
        avgQuality: input.avgQuality ?? null,
      });
    }
    return this.getByAgentAndDate(input.agentId, input.date);
  },

  /**
   * Update a daily stat by id.
   */
  async update(id: string, input: UpdateDailyStatInput) {
    const stat = await this.getById(id);
    if (input.totalQueries !== undefined)
      stat.totalQueries = input.totalQueries;
    if (input.totalTokens !== undefined) stat.totalTokens = input.totalTokens;
    if (input.avgEfficiency !== undefined)
      stat.avgEfficiency = input.avgEfficiency;
    if (input.avgQuality !== undefined) stat.avgQuality = input.avgQuality;
    await stat.save();
    return this.getById(id);
  },

  /**
   * Soft-delete a daily stat.
   */
  async delete(id: string) {
    const stat = await this.getById(id);
    await stat.update({ isDeleted: true, deletedAt: new Date() });
    return { ok: true };
  },
};
