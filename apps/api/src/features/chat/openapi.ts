import type { OpenApiFragment } from "../../openapi/base";

const schemas = {};

const paths = {
  "/api/chat/stream": {
    post: {
      summary: "Send a message to an agent and get a streaming response",
      tags: ["Chat"],
      requestBody: {
        required: true,
        content: {
          "application/json": {
            schema: {
              type: "object",
              required: ["agentId", "message"],
              properties: {
                agentId: { type: "string", format: "uuid" },
                message: { type: "string" },
              },
            },
          },
        },
      },
      responses: {
        200: { description: "Streaming text response" },
      },
    },
  },
};

const tags = [{ name: "Chat", description: "Agent chat and streaming" }];

export const chatOpenApi: OpenApiFragment = {
  paths,
  schemas,
  tags,
};
