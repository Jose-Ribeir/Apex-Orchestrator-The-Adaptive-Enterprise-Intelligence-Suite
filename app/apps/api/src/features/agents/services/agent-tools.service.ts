import { AgentTool, Agent, Tool } from "../../../models";
import { NotFoundError } from "../../../lib/errors";
import type { PageLimit } from "../../../lib/pagination";

export const agentToolService = {
  /**
   * List tools assigned to an agent (paginated).
   */
  async listByAgent(
    agentId: string,
    pagination: PageLimit,
  ): Promise<{ data: Tool[]; total: number }> {
    const agent = await Agent.findByPk(agentId);
    if (!agent) throw new NotFoundError("Agent", agentId);
    const { page, limit } = pagination;
    const offset = (page - 1) * limit;
    const { count, rows } = await AgentTool.findAndCountAll({
      where: { agentId },
      limit,
      offset,
      include: [{ model: Tool, required: true }],
    });
    const data = rows.map((r) => (r as AgentTool & { Tool: Tool }).Tool);
    return { data, total: count };
  },

  /**
   * Assign a tool to an agent (idempotent).
   */
  async addTool(agentId: string, toolId: string) {
    const [agent, tool] = await Promise.all([
      Agent.findByPk(agentId),
      Tool.findByPk(toolId),
    ]);
    if (!agent) throw new NotFoundError("Agent", agentId);
    if (!tool) throw new NotFoundError("Tool", toolId);
    await AgentTool.findOrCreate({
      where: { agentId, toolId },
      defaults: { agentId, toolId },
    });
    return { agentId, toolId };
  },

  /**
   * Remove a tool assignment from an agent.
   */
  async removeTool(agentId: string, toolId: string) {
    const deleted = await AgentTool.destroy({
      where: { agentId, toolId },
    });
    if (deleted === 0) throw new NotFoundError("AgentTool");
    return { ok: true };
  },
};
