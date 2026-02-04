import type { OpenApiFragment } from "../../openapi/base";

const schemas = {
  ApiTokenListItem: {
    type: "object",
    description:
      "API token metadata (token value is never returned after creation)",
    properties: {
      id: { type: "string", format: "uuid" },
      name: { type: "string", nullable: true },
      lastUsedAt: { type: "string", format: "date-time", nullable: true },
      expiresAt: { type: "string", format: "date-time", nullable: true },
      createdAt: { type: "string", format: "date-time" },
    },
  },
  CreateApiTokenResponse: {
    type: "object",
    description:
      "Response when creating an API token. The plain token is returned only once.",
    required: ["token", "id"],
    properties: {
      token: {
        type: "string",
        description:
          "Plain API token; store securely and use as Bearer token. Only returned once.",
      },
      id: { type: "string", format: "uuid" },
      name: { type: "string", nullable: true },
      expiresAt: { type: "string", format: "date-time", nullable: true },
    },
  },
};

const paths = {
  "/api/api-tokens": {
    post: {
      operationId: "createApiToken",
      tags: ["API Tokens"],
      summary: "Create API token",
      description:
        "Create an API token for the authenticated user. The plain token is returned only in this response; use it as Authorization: Bearer <token>.",
      requestBody: {
        content: {
          "application/json": {
            schema: {
              type: "object",
              properties: {
                name: {
                  type: "string",
                  description: "Optional label (e.g. CI, Dashboard)",
                },
                expiresInDays: {
                  type: "number",
                  description: "Optional expiry in days from now",
                },
              },
            },
          },
        },
      },
      responses: {
        201: {
          description: "Created token (plain token only returned once)",
          content: {
            "application/json": {
              schema: { $ref: "#/components/schemas/CreateApiTokenResponse" },
            },
          },
        },
      },
    },
    get: {
      operationId: "listApiTokens",
      tags: ["API Tokens"],
      summary: "List API tokens",
      description:
        "List current user's API tokens (paginated). Token values are never returned.",
      parameters: [
        {
          name: "page",
          in: "query",
          schema: { type: "integer", default: 1 },
          description: "Page (1-based)",
        },
        {
          name: "limit",
          in: "query",
          schema: { type: "integer", default: 20 },
          description: "Items per page (max 100)",
        },
      ],
      responses: {
        200: {
          description: "Paginated list of token metadata",
          content: {
            "application/json": {
              schema: {
                type: "object",
                required: ["data", "meta"],
                properties: {
                  data: {
                    type: "array",
                    items: { $ref: "#/components/schemas/ApiTokenListItem" },
                  },
                  meta: {
                    type: "object",
                    properties: {
                      pagination: {
                        $ref: "#/components/schemas/PaginationMeta",
                      },
                    },
                  },
                },
              },
            },
          },
        },
      },
    },
  },
  "/api/api-tokens/{id}": {
    delete: {
      operationId: "revokeApiToken",
      tags: ["API Tokens"],
      summary: "Revoke API token",
      parameters: [
        {
          name: "id",
          in: "path",
          required: true,
          schema: { type: "string", format: "uuid" },
        },
      ],
      responses: {
        204: { description: "Token revoked" },
        404: { description: "Token not found" },
      },
    },
  },
};

const tags = [
  {
    name: "API Tokens",
    description: "Create and manage API tokens for Bearer authentication",
  },
];

export const apiTokensOpenApi: OpenApiFragment = {
  paths,
  schemas,
  tags,
};
