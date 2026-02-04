import { AgentInstruction, Agent } from "../../../models";
import { NotFoundError, ValidationError } from "../../../lib/errors";
import type { PageLimit } from "../../../lib/pagination";

export interface CreateInstructionInput {
  agentId: string;
  content: string;
  order: number;
}

export interface UpdateInstructionInput {
  content?: string;
  order?: number;
}

export const agentInstructionService = {
  /**
   * List instructions for an agent (paginated, ordered by order).
   */
  async listByAgent(
    agentId: string,
    pagination: PageLimit,
  ): Promise<{ data: AgentInstruction[]; total: number }> {
    const { page, limit } = pagination;
    const offset = (page - 1) * limit;
    const total = await AgentInstruction.count({ where: { agentId } });
    const rows = await AgentInstruction.findAll({
      where: { agentId },
      order: [["order", "ASC"]],
      limit,
      offset,
    });
    return { data: rows, total };
  },

  /**
   * Get a single instruction by id, optionally scoped to agentId.
   */
  async getById(id: string, agentId?: string) {
    const where: { id: string; agentId?: string } = { id };
    if (agentId) where.agentId = agentId;
    const instruction = await AgentInstruction.findOne({ where });
    if (!instruction) throw new NotFoundError("AgentInstruction", id);
    return instruction;
  },

  /**
   * Create an instruction for an agent.
   */
  async create(input: CreateInstructionInput) {
    if (!input.content?.trim())
      throw new ValidationError("content is required");
    const agent = await Agent.findByPk(input.agentId);
    if (!agent) throw new NotFoundError("Agent", input.agentId);
    return AgentInstruction.create({
      agentId: input.agentId,
      content: input.content.trim(),
      order: input.order ?? 0,
    });
  },

  /**
   * Update an instruction (content and/or order).
   */
  async update(id: string, agentId: string, input: UpdateInstructionInput) {
    const instruction = await this.getById(id, agentId);
    if (input.content !== undefined) instruction.content = input.content.trim();
    if (input.order !== undefined) instruction.order = input.order;
    await instruction.save();
    return instruction;
  },

  /**
   * Soft-delete an instruction.
   */
  async delete(id: string, agentId: string) {
    const instruction = await this.getById(id, agentId);
    await instruction.update({ isDeleted: true, deletedAt: new Date() });
    return { ok: true };
  },
};
