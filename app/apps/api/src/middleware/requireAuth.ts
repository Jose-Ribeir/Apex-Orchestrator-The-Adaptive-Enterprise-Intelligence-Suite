import type { Request, Response, NextFunction } from "express";
import { QueryTypes } from "sequelize";
import { fromNodeHeaders } from "better-auth/node";
import { auth } from "../lib/auth";
import { hashToken } from "../lib/api-tokens";
import { ApiToken } from "../models";
import { sequelize } from "../config/database";

/**
 * Session shape returned by Better Auth getSession (user + session).
 * Used to type req.session in protected routes.
 */
export type AuthSession =
  Awaited<ReturnType<typeof auth.api.getSession>> extends infer R
    ? R extends null
      ? never
      : R
    : never;

/**
 * Load user from Better Auth "user" table and return shape compatible with req.user.
 */
async function loadUserById(
  userId: string,
): Promise<AuthSession["user"] | null> {
  const rows = await sequelize.query<{
    id: string;
    name: string;
    email: string;
    emailVerified: boolean;
    image: string | null;
    createdAt: Date;
    updatedAt: Date;
  }>(
    `SELECT id, name, email, "emailVerified", image, "createdAt", "updatedAt" FROM "user" WHERE id = :userId`,
    { replacements: { userId }, type: QueryTypes.SELECT },
  );
  const row = rows?.[0];
  if (!row) return null;
  return {
    id: row.id,
    name: row.name,
    email: row.email,
    emailVerified: row.emailVerified,
    image: row.image ?? undefined,
    createdAt: row.createdAt,
    updatedAt: row.updatedAt,
  };
}

/**
 * Middleware that requires an authenticated user.
 * Supports (1) Better Auth session and (2) Authorization: Bearer <api-token>.
 * On success, sets req.session (session only) and req.user for downstream handlers.
 */
export async function requireAuth(
  req: Request,
  res: Response,
  next: NextFunction,
): Promise<void> {
  const session = await auth.api.getSession({
    headers: fromNodeHeaders(req.headers),
  });

  if (session?.user) {
    (req as Request & { session: AuthSession }).session = session;
    (req as Request & { user: AuthSession["user"] }).user = session.user;
    next();
    return;
  }

  const authHeader = req.headers.authorization;
  const bearerPrefix = "bearer ";
  if (!authHeader || !authHeader.toLowerCase().startsWith(bearerPrefix)) {
    res.status(401).json({
      error: "Unauthorized",
      message: "Authentication required",
    });
    return;
  }

  const token = authHeader.slice(bearerPrefix.length).trim();
  if (!token) {
    res.status(401).json({
      error: "Unauthorized",
      message: "Authentication required",
    });
    return;
  }

  const tokenHash = hashToken(token);
  const apiToken = await ApiToken.unscoped().findOne({
    where: { tokenHash },
    attributes: ["id", "userId", "expiresAt"],
  });

  if (!apiToken) {
    res.status(401).json({
      error: "Unauthorized",
      message: "Invalid or expired token",
    });
    return;
  }

  if (
    apiToken.expiresAt &&
    new Date(apiToken.expiresAt).getTime() <= Date.now()
  ) {
    res.status(401).json({
      error: "Unauthorized",
      message: "Invalid or expired token",
    });
    return;
  }

  const user = await loadUserById(apiToken.userId);
  if (!user) {
    res.status(401).json({
      error: "Unauthorized",
      message: "User not found",
    });
    return;
  }

  await ApiToken.unscoped().update(
    { lastUsedAt: new Date() },
    { where: { id: apiToken.id } },
  );

  (req as Request & { user: AuthSession["user"] }).user = user;
  next();
}
