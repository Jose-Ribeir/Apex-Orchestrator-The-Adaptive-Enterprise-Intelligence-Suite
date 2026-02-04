import { ApiToken } from "../../models";
import { generateToken, hashToken } from "../../lib/api-tokens";
import { NotFoundError } from "../../lib/errors";
import type { PageLimit } from "../../lib/pagination";

export interface CreateTokenOptions {
  name?: string | null;
  expiresAt?: Date | null;
}

export interface CreateTokenResult {
  token: string;
  id: string;
  name: string | null;
  expiresAt: Date | null;
}

export const apiTokensService = {
  /**
   * Create an API token for a user. Returns the plain token only in this response.
   */
  async createToken(
    userId: string,
    options: CreateTokenOptions = {},
  ): Promise<CreateTokenResult> {
    const token = generateToken();
    const tokenHash = hashToken(token);
    const record = await ApiToken.unscoped().create({
      userId,
      tokenHash,
      name: options.name?.trim() || null,
      expiresAt: options.expiresAt ?? null,
    });
    return {
      token,
      id: record.id,
      name: record.name,
      expiresAt: record.expiresAt,
    };
  },

  /**
   * List API tokens for a user (without token values), paginated.
   */
  async listByUserId(
    userId: string,
    pagination: PageLimit,
  ): Promise<{ data: ApiToken[]; total: number }> {
    const { page, limit } = pagination;
    const offset = (page - 1) * limit;
    const { count, rows } = await ApiToken.unscoped().findAndCountAll({
      where: { userId },
      order: [["createdAt", "DESC"]],
      attributes: ["id", "name", "lastUsedAt", "expiresAt", "createdAt"],
      limit,
      offset,
    });
    return { data: rows, total: count };
  },

  /**
   * Revoke an API token by id, scoped to userId.
   */
  async revoke(id: string, userId: string) {
    const deleted = await ApiToken.unscoped().destroy({
      where: { id, userId },
    });
    if (deleted === 0) throw new NotFoundError("API token", id);
    return { ok: true };
  },
};
