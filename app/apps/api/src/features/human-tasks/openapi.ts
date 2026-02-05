import type { OpenApiFragment } from "../../openapi/base";

const schemas = {
  HumanTask: {
    type: "object",
    properties: {
      id: { type: "string", format: "uuid" },
      modelQueryId: { type: "string", format: "uuid" },
      reason: { type: "string" },
      retrievedData: { type: "string", nullable: true },
      modelMessage: { type: "string" },
      status: { type: "string", enum: ["PENDING", "RESOLVED"] },
      createdAt: { type: "string", format: "date-time" },
      updatedAt: { type: "string", format: "date-time" },
    },
  },
};

const paths = {
  "/api/human-tasks": {
    get: {
      operationId: "listHumanTasks",
      tags: ["Human Tasks"],
      summary: "List human tasks",
      parameters: [
        {
          name: "pending",
          in: "query",
          schema: { type: "boolean" },
          description: "Only PENDING",
        },
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
          description: "Paginated list of human tasks",
          content: {
            "application/json": {
              schema: {
                type: "object",
                required: ["data", "meta"],
                properties: {
                  data: {
                    type: "array",
                    items: { $ref: "#/components/schemas/HumanTask" },
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
      operationId: "createHumanTask",
      tags: ["Human Tasks"],
      summary: "Create human task",
      requestBody: {
        required: true,
        content: {
          "application/json": {
            schema: {
              type: "object",
              required: ["modelQueryId", "reason", "modelMessage"],
              properties: {
                modelQueryId: { type: "string" },
                reason: { type: "string" },
                retrievedData: { type: "string" },
                modelMessage: { type: "string" },
                status: { type: "string", enum: ["PENDING", "RESOLVED"] },
              },
            },
          },
        },
      },
      responses: { 201: { description: "Created human task" } },
    },
  },
  "/api/human-tasks/{id}": {
    get: {
      operationId: "getHumanTaskById",
      tags: ["Human Tasks"],
      summary: "Get human task",
      parameters: [
        {
          name: "id",
          in: "path",
          required: true,
          schema: { type: "string" },
        },
      ],
      responses: { 200: { description: "Human task" } },
    },
    patch: {
      operationId: "updateHumanTask",
      tags: ["Human Tasks"],
      summary: "Update human task",
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
              properties: {
                reason: { type: "string" },
                retrievedData: { type: "string" },
                modelMessage: { type: "string" },
                status: { type: "string", enum: ["PENDING", "RESOLVED"] },
              },
            },
          },
        },
      },
      responses: { 200: { description: "Updated human task" } },
    },
    delete: {
      operationId: "deleteHumanTask",
      tags: ["Human Tasks"],
      summary: "Delete human task",
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
  "/api/human-tasks/{id}/resolve": {
    post: {
      operationId: "resolveHumanTask",
      tags: ["Human Tasks"],
      summary: "Resolve human task",
      parameters: [
        {
          name: "id",
          in: "path",
          required: true,
          schema: { type: "string" },
        },
      ],
      responses: { 200: { description: "Resolved" } },
    },
  },
};

const tags = [{ name: "Human Tasks", description: "Human-in-the-loop tasks" }];

export const humanTasksOpenApi: OpenApiFragment = {
  paths,
  schemas,
  tags,
};
