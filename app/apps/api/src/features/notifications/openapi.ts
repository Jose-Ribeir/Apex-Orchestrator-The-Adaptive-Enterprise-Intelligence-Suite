import type { OpenApiFragment } from "../../openapi/base";

const schemas = {
  Notification: {
    type: "object",
    properties: {
      id: { type: "string", format: "uuid" },
      userId: { type: "string" },
      type: {
        type: "string",
        enum: [
          "HUMAN_TASK_CREATED",
          "AGENT_ERROR",
          "PERFORMANCE_ALERT",
          "SYSTEM",
        ],
      },
      title: { type: "string" },
      message: { type: "string" },
      isRead: { type: "boolean" },
      createdAt: { type: "string", format: "date-time" },
      updatedAt: { type: "string", format: "date-time" },
    },
  },
};

const paths = {
  "/api/notifications": {
    get: {
      operationId: "listNotifications",
      tags: ["Notifications"],
      summary: "List notifications",
      parameters: [
        { name: "unread", in: "query", schema: { type: "boolean" } },
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
          description: "Paginated list of notifications",
          content: {
            "application/json": {
              schema: {
                type: "object",
                required: ["data", "meta"],
                properties: {
                  data: {
                    type: "array",
                    items: { $ref: "#/components/schemas/Notification" },
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
  "/api/notifications/mark-all-read": {
    post: {
      operationId: "markAllNotificationsRead",
      tags: ["Notifications"],
      summary: "Mark all notifications as read",
      responses: { 200: { description: "OK" } },
    },
  },
  "/api/notifications/{id}": {
    get: {
      operationId: "getNotificationById",
      tags: ["Notifications"],
      summary: "Get notification",
      parameters: [
        {
          name: "id",
          in: "path",
          required: true,
          schema: { type: "string" },
        },
      ],
      responses: { 200: { description: "Notification" } },
    },
  },
  "/api/notifications/{id}/read": {
    post: {
      operationId: "markNotificationRead",
      tags: ["Notifications"],
      summary: "Mark notification as read",
      parameters: [
        {
          name: "id",
          in: "path",
          required: true,
          schema: { type: "string" },
        },
      ],
      responses: { 200: { description: "Updated notification" } },
    },
  },
};

const tags = [{ name: "Notifications", description: "User notifications" }];

export const notificationsOpenApi: OpenApiFragment = {
  paths,
  schemas,
  tags,
};
