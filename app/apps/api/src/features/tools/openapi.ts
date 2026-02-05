import type { OpenApiFragment } from "../../openapi/base";

const schemas = {
  Tool: {
    type: "object",
    properties: {
      id: { type: "string", format: "uuid" },
      name: { type: "string" },
      createdAt: { type: "string", format: "date-time" },
      updatedAt: { type: "string", format: "date-time" },
    },
  },
};

const paths = {
  "/api/tools": {
    get: {
      operationId: "listTools",
      tags: ["Tools"],
      summary: "List tools",
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
          description: "Paginated list of tools",
          content: {
            "application/json": {
              schema: {
                type: "object",
                required: ["data", "meta"],
                properties: {
                  data: {
                    type: "array",
                    items: { $ref: "#/components/schemas/Tool" },
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
    post: {
      operationId: "createTool",
      tags: ["Tools"],
      summary: "Create tool",
      requestBody: {
        required: true,
        content: {
          "application/json": {
            schema: {
              type: "object",
              required: ["name"],
              properties: { name: { type: "string" } },
            },
          },
        },
      },
      responses: { 201: { description: "Created tool" } },
    },
  },
  "/api/tools/{id}": {
    get: {
      operationId: "getToolById",
      tags: ["Tools"],
      summary: "Get tool",
      parameters: [
        {
          name: "id",
          in: "path",
          required: true,
          schema: { type: "string" },
        },
      ],
      responses: { 200: { description: "Tool" } },
    },
    patch: {
      operationId: "updateTool",
      tags: ["Tools"],
      summary: "Update tool",
      parameters: [
        {
          name: "id",
          in: "path",
          required: true,
          schema: { type: "string" },
        },
      ],
      requestBody: {
        content: {
          "application/json": {
            schema: {
              type: "object",
              properties: { name: { type: "string" } },
            },
          },
        },
      },
      responses: { 200: { description: "Updated tool" } },
    },
    delete: {
      operationId: "deleteTool",
      tags: ["Tools"],
      summary: "Delete tool",
      parameters: [
        {
          name: "id",
          in: "path",
          required: true,
          schema: { type: "string" },
        },
      ],
      responses: { 204: { description: "Deleted" } },
    },
  },
};

const tags = [{ name: "Tools", description: "Tool catalog" }];

export const toolsOpenApi: OpenApiFragment = {
  paths,
  schemas,
  tags,
};
