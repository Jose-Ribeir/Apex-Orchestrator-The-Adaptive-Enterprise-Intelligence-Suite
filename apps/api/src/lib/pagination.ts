import type { Request } from "express";

export const DEFAULT_PAGE_SIZE = 20;
export const MAX_PAGE_SIZE = 100;

export interface PageLimit {
  page: number;
  limit: number;
}

export interface PaginationMeta {
  page: number;
  limit: number;
  total: number;
  pages: number;
  more: boolean;
}

export interface PaginatedResponse<T> {
  data: T[];
  meta: { pagination: PaginationMeta };
}

/**
 * Parse page and limit from request query (1-based page).
 * Default: page=1, limit=20. Cap limit at MAX_PAGE_SIZE.
 */
export function parsePageLimit(req: Request): PageLimit {
  const page = Math.max(1, parseInt(String(req.query.page), 10) || 1);
  const limit = Math.min(
    MAX_PAGE_SIZE,
    Math.max(1, parseInt(String(req.query.limit), 10) || DEFAULT_PAGE_SIZE),
  );
  return { page, limit };
}

/**
 * Build paginated JSON response: { data, meta: { pagination: { page, limit, total, pages, more } } }.
 * more is true when there is at least one more page after the current.
 */
export function paginatedResponse<T>(
  data: T[],
  total: number,
  page: number,
  limit: number,
): PaginatedResponse<T> {
  const pages = limit > 0 ? Math.ceil(total / limit) : 0;
  const more = page * limit < total;
  return {
    data,
    meta: {
      pagination: {
        page,
        limit,
        total,
        pages,
        more,
      },
    },
  };
}
