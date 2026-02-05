import { Agent, AgentInstruction, Tool } from "../../../models";
import { NotFoundError, ValidationError } from "../../../lib/errors";
import type { AgentMode } from "../../../models/Agent";
import type { PageLimit } from "../../../lib/pagination";

export interface AgentInstructionResponse {
  id: string;
  content: string;
  order: number;
  createdAt: string;
  updatedAt: string;
}

export interface ToolResponse {
  id: string;
  name: string;
  createdAt: string;
  updatedAt: string;
}

export interface AgentResponse {
  id: string;
  userId: string;
  name: string;
  mode: AgentMode;
  prompt: string | null;
  createdAt: string;
  updatedAt: string;
  instructions: AgentInstructionResponse[];
  tools: ToolResponse[];
}

function toAgentResponse(agent: Agent): AgentResponse {
  const a = agent.get({ plain: true }) as {
    id: string;
    userId: string;
    name: string;
    mode: AgentMode;
    prompt: string | null;
    createdAt: Date;
    updatedAt: Date;
    instructions?: Array<{
      id: string;
      content: string;
      order: number;
      createdAt: Date;
      updatedAt: Date;
    }>;
    tools?: Array<{
      id: string;
      name: string;
      createdAt: Date;
      updatedAt: Date;
    }>;
  };
  return {
    id: a.id,
    userId: a.userId,
    name: a.name,
    mode: a.mode,
    prompt: a.prompt ?? null,
    createdAt:
      a.createdAt instanceof Date
        ? a.createdAt.toISOString()
        : (a.createdAt as unknown as string),
    updatedAt:
      a.updatedAt instanceof Date
        ? a.updatedAt.toISOString()
        : (a.updatedAt as unknown as string),
    instructions: (a.instructions ?? []).map((i) => ({
      id: i.id,
      content: i.content,
      order: i.order,
      createdAt:
        i.createdAt instanceof Date
          ? i.createdAt.toISOString()
          : (i.createdAt as unknown as string),
      updatedAt:
        i.updatedAt instanceof Date
          ? i.updatedAt.toISOString()
          : (i.updatedAt as unknown as string),
    })),
    tools: (a.tools ?? []).map((t) => ({
      id: t.id,
      name: t.name,
      createdAt:
        t.createdAt instanceof Date
          ? t.createdAt.toISOString()
          : (t.createdAt as unknown as string),
      updatedAt:
        t.updatedAt instanceof Date
          ? t.updatedAt.toISOString()
          : (t.updatedAt as unknown as string),
    })),
  };
}

export interface CreateAgentInput {
  userId: string;
  name: string;
  mode: AgentMode;
  prompt?: string | null;
  instructions?: string[];
  tools?: string[];
}

export interface UpdateAgentInput {
  name?: string;
  mode?: AgentMode;
  prompt?: string | null;
  instructions?: string[];
  tools?: string[];
}

export const agentService = {
  /**
   * List agents for a user with pagination.
   * @param userId - Owner user id
   * @param pagination - page and limit
   * @returns Paginated list of agents with instructions and tools
   */
  async listByUser(
    userId: string,
    pagination: PageLimit,
  ): Promise<{ data: AgentResponse[]; total: number }> {
    const { page, limit } = pagination;
    const offset = (page - 1) * limit;
    const where = { userId };
    const { count, rows: agents } = await Agent.findAndCountAll({
      where,
      distinct: true,
      col: "id",
      order: [["createdAt", "DESC"]],
      limit,
      offset,
      include: [
        {
          model: AgentInstruction,
          as: "instructions",
          order: [["order", "ASC"]],
        },
        { model: Tool, as: "tools", through: { attributes: [] } },
      ],
    });
    return { data: agents.map(toAgentResponse), total: count };
  },

  /**
   * Get a single agent by id, optionally scoped to userId.
   * @param id - Agent UUID
   * @param userId - If provided, restricts to this user's agent
   * @throws NotFoundError if agent not found
   */
  async getById(id: string, userId?: string): Promise<AgentResponse> {
    const where: { id: string; userId?: string } = { id };
    if (userId) where.userId = userId;
    const agent = await Agent.findOne({
      where,
      include: [
        {
          model: AgentInstruction,
          as: "instructions",
          order: [["order", "ASC"]],
        },
        { model: Tool, as: "tools", through: { attributes: [] } },
      ],
    });
    if (!agent) throw new NotFoundError("Agent", id);
    return toAgentResponse(agent);
  },

  /**
   * Create a new agent with optional instructions and tool assignments.
   */
  async create(input: CreateAgentInput) {
    if (!input.name?.trim()) throw new ValidationError("name is required");
    const agent = await Agent.create({
      userId: input.userId,
      name: input.name.trim(),
      mode: input.mode ?? "EFFICIENCY",
      prompt: input.prompt?.trim() ?? null,
    });
    if (input.instructions?.length) {
      for (let i = 0; i < input.instructions.length; i++) {
        const content = (input.instructions[i] ?? "").trim();
        if (content) {
          await AgentInstruction.create({
            agentId: agent.id,
            content,
            order: i,
          });
        }
      }
    }
    if (input.tools?.length) {
      await agent.setTools(input.tools);
    }
    return this.getById(agent.id);
  },

  /**
   * Update an agent; partial updates supported.
   */
  async update(id: string, userId: string, input: UpdateAgentInput) {
    const agent = await Agent.findOne({
      where: { id, userId },
      include: [
        {
          model: AgentInstruction,
          as: "instructions",
          order: [["order", "ASC"]],
        },
        { model: Tool, as: "tools", through: { attributes: [] } },
      ],
    });
    if (!agent) throw new NotFoundError("Agent", id);
    if (input.name !== undefined) agent.name = input.name.trim();
    if (input.mode !== undefined) agent.mode = input.mode;
    if (input.prompt !== undefined) agent.prompt = input.prompt?.trim() ?? null;
    if (input.instructions !== undefined) {
      await agent.setInstructions(input.instructions as unknown as string[]);
    }
    if (input.tools !== undefined) {
      await agent.setTools(input.tools);
    }
    await agent.save();
    return this.getById(agent.id);
  },

  /**
   * Soft-delete an agent by id (user-scoped).
   */
  async delete(id: string, userId: string) {
    const agent = await Agent.findOne({ where: { id, userId } });
    if (!agent) throw new NotFoundError("Agent", id);
    await agent.update({ isDeleted: true, deletedAt: new Date() });
    return { ok: true };
  },
};
