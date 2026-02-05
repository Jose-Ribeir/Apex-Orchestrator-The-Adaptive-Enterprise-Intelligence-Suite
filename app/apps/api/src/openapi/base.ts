import { env } from "../config/env";

export const openApiBase = {
  openapi: "3.0.3" as const,
  info: {
    title: "AI Router API",
    version: "1.0.0",
    description:
      "Backend API for agents, queries, human tasks, metrics, and notifications. Authenticate with a session cookie (Better Auth) or with `Authorization: Bearer <api-token>`.",
  },
  servers: [{ url: `http://localhost:${env.port}`, description: "Local" }],
  components: {
    securitySchemes: {
      BearerAuth: {
        type: "http" as const,
        scheme: "bearer",
        bearerFormat: "API token",
        description:
          "API token from POST /api/api-tokens. Sent as Authorization: Bearer <token>.",
      },
    },
    schemas: {
      PaginationMeta: {
        type: "object",
        properties: {
          page: { type: "integer", description: "Current page" },
          limit: { type: "integer", description: "Page size" },
          total: { type: "integer", description: "Total number of items" },
          pages: {
            type: "integer",
            description: "Total number of pages available",
          },
          more: {
            type: "boolean",
            description: "True if there is at least one more page after this",
          },
        },
        required: ["page", "limit", "total", "pages", "more"],
      },
    },
  },
};

export type OpenApiFragment = {
  paths: Record<string, unknown>;
  schemas: Record<string, unknown>;
  tags: Array<{ name: string; description?: string }>;
};
