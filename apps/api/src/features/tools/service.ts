import { Tool } from "../../models";
import { NotFoundError, ValidationError } from "../../lib/errors";
import type { PageLimit } from "../../lib/pagination";

export const toolService = {
  /**
   * List tools with pagination, ordered by name.
   * @param pagination - page and limit
   * @returns Paginated list of tools and total count
   */
  async list(pagination: PageLimit): Promise<{ data: Tool[]; total: number }> {
    const { page, limit } = pagination;
    const offset = (page - 1) * limit;
    const { count, rows } = await Tool.findAndCountAll({
      order: [["name", "ASC"]],
      limit,
      offset,
    });
    return { data: rows, total: count };
  },

  /**
   * Fetch a single tool by id.
   * @param id - UUID of the tool
   * @throws NotFoundError if tool does not exist
   */
  async getById(id: string) {
    const tool = await Tool.findByPk(id);
    if (!tool) throw new NotFoundError("Tool", id);
    return tool;
  },

  /**
   * Create a new tool.
   * @param name - Display name (required, trimmed)
   * @throws ValidationError if name is empty
   */
  async create(name: string) {
    if (!name?.trim()) throw new ValidationError("name is required");
    return Tool.create({ name: name.trim() });
  },

  /**
   * Update an existing tool's name.
   * @param id - UUID of the tool
   * @param name - New name (required, trimmed)
   * @throws ValidationError if name is empty
   */
  async update(id: string, name: string) {
    if (!name?.trim()) throw new ValidationError("name is required");
    const tool = await this.getById(id);
    await tool.update({ name: name.trim() });
    return tool;
  },

  /**
   * Soft-delete a tool by id.
   * @param id - UUID of the tool
   */
  async delete(id: string) {
    const tool = await this.getById(id);
    await tool.update({ isDeleted: true, deletedAt: new Date() });
    return { ok: true };
  },
};
