import type { OpenApiFragment } from "../../openapi/base";

const schemas = {
  Agent: {
    type: "object",
    properties: {
      id: { type: "string", format: "uuid" },
      userId: { type: "string" },
      name: { type: "string" },
      mode: { type: "string", enum: ["PERFORMANCE", "EFFICIENCY"] },
      prompt: {
        type: "string",
        nullable: true,
        description: "System prompt for the agent",
      },
      createdAt: { type: "string", format: "date-time" },
      updatedAt: { type: "string", format: "date-time" },
      instructions: {
        type: "array",
        items: { $ref: "#/components/schemas/AgentInstruction" },
        description: "Ordered instructions for this agent",
      },
      tools: {
        type: "array",
        items: { $ref: "#/components/schemas/Tool" },
        description: "Tools assigned to this agent",
      },
    },
  },
  AgentInstruction: {
    type: "object",
    properties: {
      id: { type: "string", format: "uuid" },
      agentId: { type: "string", format: "uuid" },
      content: { type: "string" },
      order: { type: "integer" },
      createdAt: { type: "string", format: "date-time" },
      updatedAt: { type: "string", format: "date-time" },
    },
  },
  ModelQuery: {
    type: "object",
    properties: {
      id: { type: "string", format: "uuid" },
      agentId: { type: "string", format: "uuid" },
      userQuery: { type: "string" },
      modelResponse: { type: "string", nullable: true },
      methodUsed: { type: "string", enum: ["PERFORMANCE", "EFFICIENCY"] },
      createdAt: { type: "string", format: "date-time" },
      updatedAt: { type: "string", format: "date-time" },
    },
  },
  DailyStat: {
    type: "object",
    properties: {
      id: { type: "string", format: "uuid" },
      agentId: { type: "string", format: "uuid" },
      date: { type: "string", format: "date" },
      totalQueries: { type: "integer" },
      totalTokens: { type: "integer" },
      avgEfficiency: { type: "number", nullable: true },
      avgQuality: { type: "number", nullable: true },
      createdAt: { type: "string", format: "date-time" },
      updatedAt: { type: "string", format: "date-time" },
    },
  },
};

const paths = {
  "/api/agents": {
    get: {
      operationId: "listAgents",
      tags: ["Agents"],
      summary: "List agents",
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
          description: "Paginated list of agents",
          content: {
            "application/json": {
              schema: {
                type: "object",
                required: ["data", "meta"],
                properties: {
                  data: {
                    type: "array",
                    items: { $ref: "#/components/schemas/Agent" },
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
      operationId: "createAgent",
      tags: ["Agents"],
      summary: "Create agent",
      requestBody: {
        required: true,
        content: {
          "application/json": {
            schema: {
              type: "object",
              required: ["name"],
              properties: {
                name: { type: "string" },
                mode: { type: "string", enum: ["PERFORMANCE", "EFFICIENCY"] },
                prompt: {
                  type: "string",
                  nullable: true,
                  description: "System prompt for the agent",
                },
                instructions: {
                  type: "array",
                  items: { type: "string" },
                  description: "Instruction IDs",
                },
                tools: {
                  type: "array",
                  items: { type: "string" },
                  description: "Tool IDs",
                },
              },
            },
          },
        },
      },
      responses: {
        201: {
          description: "Created agent",
          content: {
            "application/json": {
              schema: { $ref: "#/components/schemas/Agent" },
            },
          },
        },
      },
    },
  },
  "/api/agents/{id}": {
    get: {
      operationId: "getAgentById",
      tags: ["Agents"],
      summary: "Get agent by ID",
      parameters: [
        {
          name: "id",
          in: "path",
          required: true,
          schema: { type: "string" },
        },
      ],
      responses: {
        200: {
          description: "Agent",
          content: {
            "application/json": {
              schema: { $ref: "#/components/schemas/Agent" },
            },
          },
        },
        404: { description: "Not found" },
      },
    },
    patch: {
      operationId: "updateAgent",
      tags: ["Agents"],
      summary: "Update agent",
      parameters: [
        {
          name: "id",
          in: "path",
          required: true,
          schema: { type: "string" },
        },
      ],
      requestBody: {
        required: true,
        content: {
          "application/json": {
            schema: {
              type: "object",
              properties: {
                name: { type: "string" },
                mode: { type: "string", enum: ["PERFORMANCE", "EFFICIENCY"] },
                prompt: {
                  type: "string",
                  nullable: true,
                  description: "System prompt for the agent",
                },
                instructions: {
                  type: "array",
                  items: { type: "string" },
                  description: "Instruction IDs",
                },
                tools: {
                  type: "array",
                  items: { type: "string" },
                  description: "Tool IDs",
                },
              },
            },
          },
        },
      },
      responses: {
        200: {
          description: "Updated agent",
          content: {
            "application/json": {
              schema: { $ref: "#/components/schemas/Agent" },
            },
          },
        },
        404: { description: "Not found" },
      },
    },
    delete: {
      operationId: "deleteAgent",
      tags: ["Agents"],
      summary: "Delete agent",
      parameters: [
        {
          name: "id",
          in: "path",
          required: true,
          schema: { type: "string" },
        },
      ],
      responses: {
        204: { description: "Deleted" },
        404: { description: "Not found" },
      },
    },
  },
  "/api/agents/{agentId}/instructions": {
    get: {
      operationId: "listAgentInstructions",
      tags: ["Agents"],
      summary: "List instructions for an agent",
      parameters: [
        {
          name: "agentId",
          in: "path",
          required: true,
          schema: { type: "string", format: "uuid" },
        },
        { name: "page", in: "query", schema: { type: "integer", default: 1 } },
        {
          name: "limit",
          in: "query",
          schema: { type: "integer", default: 20 },
        },
      ],
      responses: {
        200: {
          description: "Paginated list of instructions",
          content: {
            "application/json": {
              schema: {
                type: "object",
                properties: {
                  data: {
                    type: "array",
                    items: { $ref: "#/components/schemas/AgentInstruction" },
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
      operationId: "createAgentInstruction",
      tags: ["Agents"],
      summary: "Create instruction for an agent",
      parameters: [
        {
          name: "agentId",
          in: "path",
          required: true,
          schema: { type: "string", format: "uuid" },
        },
      ],
      requestBody: {
        required: true,
        content: {
          "application/json": {
            schema: {
              type: "object",
              required: ["content"],
              properties: {
                content: { type: "string" },
                order: { type: "integer", default: 0 },
              },
            },
          },
        },
      },
      responses: {
        201: {
          description: "Created instruction",
          content: {
            "application/json": {
              schema: { $ref: "#/components/schemas/AgentInstruction" },
            },
          },
        },
        404: { description: "Agent not found" },
      },
    },
  },
  "/api/agents/{agentId}/instructions/{id}": {
    get: {
      operationId: "getAgentInstructionById",
      tags: ["Agents"],
      summary: "Get instruction by ID",
      parameters: [
        {
          name: "agentId",
          in: "path",
          required: true,
          schema: { type: "string", format: "uuid" },
        },
        {
          name: "id",
          in: "path",
          required: true,
          schema: { type: "string", format: "uuid" },
        },
      ],
      responses: {
        200: {
          description: "Instruction",
          content: {
            "application/json": {
              schema: { $ref: "#/components/schemas/AgentInstruction" },
            },
          },
        },
        404: { description: "Not found" },
      },
    },
    patch: {
      operationId: "updateAgentInstruction",
      tags: ["Agents"],
      summary: "Update instruction",
      parameters: [
        {
          name: "agentId",
          in: "path",
          required: true,
          schema: { type: "string", format: "uuid" },
        },
        {
          name: "id",
          in: "path",
          required: true,
          schema: { type: "string", format: "uuid" },
        },
      ],
      requestBody: {
        content: {
          "application/json": {
            schema: {
              type: "object",
              properties: {
                content: { type: "string" },
                order: { type: "integer" },
              },
            },
          },
        },
      },
      responses: {
        200: {
          description: "Updated instruction",
          content: {
            "application/json": {
              schema: { $ref: "#/components/schemas/AgentInstruction" },
            },
          },
        },
        404: { description: "Not found" },
      },
    },
    delete: {
      operationId: "deleteAgentInstruction",
      tags: ["Agents"],
      summary: "Delete instruction",
      parameters: [
        {
          name: "agentId",
          in: "path",
          required: true,
          schema: { type: "string", format: "uuid" },
        },
        {
          name: "id",
          in: "path",
          required: true,
          schema: { type: "string", format: "uuid" },
        },
      ],
      responses: {
        204: { description: "Deleted" },
        404: { description: "Not found" },
      },
    },
  },
  "/api/agents/{agentId}/tools": {
    get: {
      operationId: "listAgentTools",
      tags: ["Agents"],
      summary: "List tools assigned to an agent",
      parameters: [
        {
          name: "agentId",
          in: "path",
          required: true,
          schema: { type: "string", format: "uuid" },
        },
        { name: "page", in: "query", schema: { type: "integer", default: 1 } },
        {
          name: "limit",
          in: "query",
          schema: { type: "integer", default: 20 },
        },
      ],
      responses: {
        200: {
          description: "Paginated list of tools",
          content: {
            "application/json": {
              schema: {
                type: "object",
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
      operationId: "addAgentTool",
      tags: ["Agents"],
      summary: "Assign a tool to an agent",
      parameters: [
        {
          name: "agentId",
          in: "path",
          required: true,
          schema: { type: "string", format: "uuid" },
        },
      ],
      requestBody: {
        required: true,
        content: {
          "application/json": {
            schema: {
              type: "object",
              required: ["toolId"],
              properties: { toolId: { type: "string", format: "uuid" } },
            },
          },
        },
      },
      responses: {
        201: {
          description: "Tool assigned",
          content: {
            "application/json": {
              schema: { $ref: "#/components/schemas/Tool" },
            },
          },
        },
        404: { description: "Agent or tool not found" },
      },
    },
  },
  "/api/agents/{agentId}/tools/{toolId}": {
    delete: {
      operationId: "removeAgentTool",
      tags: ["Agents"],
      summary: "Remove tool assignment from an agent",
      parameters: [
        {
          name: "agentId",
          in: "path",
          required: true,
          schema: { type: "string", format: "uuid" },
        },
        {
          name: "toolId",
          in: "path",
          required: true,
          schema: { type: "string", format: "uuid" },
        },
      ],
      responses: {
        204: { description: "Removed" },
        404: { description: "Not found" },
      },
    },
  },
  "/api/agents/{agentId}/queries": {
    get: {
      operationId: "listAgentQueries",
      tags: ["Agents"],
      summary: "List model queries for an agent",
      parameters: [
        {
          name: "agentId",
          in: "path",
          required: true,
          schema: { type: "string", format: "uuid" },
        },
        { name: "page", in: "query", schema: { type: "integer", default: 1 } },
        {
          name: "limit",
          in: "query",
          schema: { type: "integer", default: 20 },
        },
      ],
      responses: {
        200: {
          description: "Paginated list of model queries",
          content: {
            "application/json": {
              schema: {
                type: "object",
                properties: {
                  data: {
                    type: "array",
                    items: { $ref: "#/components/schemas/ModelQuery" },
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
      operationId: "createAgentQuery",
      tags: ["Agents"],
      summary: "Create a model query for an agent",
      parameters: [
        {
          name: "agentId",
          in: "path",
          required: true,
          schema: { type: "string", format: "uuid" },
        },
      ],
      requestBody: {
        required: true,
        content: {
          "application/json": {
            schema: {
              type: "object",
              required: ["userQuery"],
              properties: {
                userQuery: { type: "string" },
                modelResponse: { type: "string", nullable: true },
                methodUsed: {
                  type: "string",
                  enum: ["PERFORMANCE", "EFFICIENCY"],
                },
              },
            },
          },
        },
      },
      responses: {
        201: {
          description: "Created model query",
          content: {
            "application/json": {
              schema: { $ref: "#/components/schemas/ModelQuery" },
            },
          },
        },
        404: { description: "Agent not found" },
      },
    },
  },
  "/api/agents/{agentId}/queries/{id}": {
    get: {
      operationId: "getAgentQueryById",
      tags: ["Agents"],
      summary: "Get model query by ID",
      parameters: [
        {
          name: "agentId",
          in: "path",
          required: true,
          schema: { type: "string", format: "uuid" },
        },
        {
          name: "id",
          in: "path",
          required: true,
          schema: { type: "string", format: "uuid" },
        },
      ],
      responses: {
        200: {
          description: "Model query",
          content: {
            "application/json": {
              schema: { $ref: "#/components/schemas/ModelQuery" },
            },
          },
        },
        404: { description: "Not found" },
      },
    },
    patch: {
      operationId: "updateAgentQuery",
      tags: ["Agents"],
      summary: "Update model query",
      parameters: [
        {
          name: "agentId",
          in: "path",
          required: true,
          schema: { type: "string", format: "uuid" },
        },
        {
          name: "id",
          in: "path",
          required: true,
          schema: { type: "string", format: "uuid" },
        },
      ],
      requestBody: {
        content: {
          "application/json": {
            schema: {
              type: "object",
              properties: {
                modelResponse: { type: "string", nullable: true },
              },
            },
          },
        },
      },
      responses: {
        200: {
          description: "Updated model query",
          content: {
            "application/json": {
              schema: { $ref: "#/components/schemas/ModelQuery" },
            },
          },
        },
        404: { description: "Not found" },
      },
    },
    delete: {
      operationId: "deleteAgentQuery",
      tags: ["Agents"],
      summary: "Delete model query",
      parameters: [
        {
          name: "agentId",
          in: "path",
          required: true,
          schema: { type: "string", format: "uuid" },
        },
        {
          name: "id",
          in: "path",
          required: true,
          schema: { type: "string", format: "uuid" },
        },
      ],
      responses: {
        204: { description: "Deleted" },
        404: { description: "Not found" },
      },
    },
  },
  "/api/agents/{agentId}/stats": {
    get: {
      operationId: "listAgentStats",
      tags: ["Agents"],
      summary: "List daily stats for an agent",
      parameters: [
        {
          name: "agentId",
          in: "path",
          required: true,
          schema: { type: "string", format: "uuid" },
        },
        {
          name: "from",
          in: "query",
          schema: {
            type: "string",
            format: "date",
            description: "Start date (YYYY-MM-DD)",
          },
        },
        {
          name: "to",
          in: "query",
          schema: {
            type: "string",
            format: "date",
            description: "End date (YYYY-MM-DD)",
          },
        },
        { name: "page", in: "query", schema: { type: "integer", default: 1 } },
        {
          name: "limit",
          in: "query",
          schema: { type: "integer", default: 20 },
        },
      ],
      responses: {
        200: {
          description: "Paginated list of daily stats",
          content: {
            "application/json": {
              schema: {
                type: "object",
                properties: {
                  data: {
                    type: "array",
                    items: { $ref: "#/components/schemas/DailyStat" },
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
      operationId: "createAgentStat",
      tags: ["Agents"],
      summary: "Create daily stat for an agent",
      parameters: [
        {
          name: "agentId",
          in: "path",
          required: true,
          schema: { type: "string", format: "uuid" },
        },
      ],
      requestBody: {
        required: true,
        content: {
          "application/json": {
            schema: {
              type: "object",
              required: ["date", "totalQueries", "totalTokens"],
              properties: {
                date: { type: "string", format: "date" },
                totalQueries: { type: "integer" },
                totalTokens: { type: "integer" },
                avgEfficiency: { type: "number", nullable: true },
                avgQuality: { type: "number", nullable: true },
              },
            },
          },
        },
      },
      responses: {
        201: {
          description: "Created daily stat",
          content: {
            "application/json": {
              schema: { $ref: "#/components/schemas/DailyStat" },
            },
          },
        },
        404: { description: "Agent not found" },
      },
    },
  },
  "/api/agents/{agentId}/stats/date/{date}": {
    get: {
      operationId: "getAgentStatByDate",
      tags: ["Agents"],
      summary: "Get daily stat by agent and date",
      parameters: [
        {
          name: "agentId",
          in: "path",
          required: true,
          schema: { type: "string", format: "uuid" },
        },
        {
          name: "date",
          in: "path",
          required: true,
          schema: { type: "string", description: "YYYY-MM-DD" },
        },
      ],
      responses: {
        200: {
          description: "Daily stat",
          content: {
            "application/json": {
              schema: { $ref: "#/components/schemas/DailyStat" },
            },
          },
        },
        404: { description: "Not found" },
      },
    },
  },
  "/api/agents/{agentId}/stats/{id}": {
    get: {
      operationId: "getAgentStatById",
      tags: ["Agents"],
      summary: "Get daily stat by ID",
      parameters: [
        {
          name: "agentId",
          in: "path",
          required: true,
          schema: { type: "string", format: "uuid" },
        },
        {
          name: "id",
          in: "path",
          required: true,
          schema: { type: "string", format: "uuid" },
        },
      ],
      responses: {
        200: {
          description: "Daily stat",
          content: {
            "application/json": {
              schema: { $ref: "#/components/schemas/DailyStat" },
            },
          },
        },
        404: { description: "Not found" },
      },
    },
    patch: {
      operationId: "updateAgentStat",
      tags: ["Agents"],
      summary: "Update daily stat",
      parameters: [
        {
          name: "agentId",
          in: "path",
          required: true,
          schema: { type: "string", format: "uuid" },
        },
        {
          name: "id",
          in: "path",
          required: true,
          schema: { type: "string", format: "uuid" },
        },
      ],
      requestBody: {
        content: {
          "application/json": {
            schema: {
              type: "object",
              properties: {
                totalQueries: { type: "integer" },
                totalTokens: { type: "integer" },
                avgEfficiency: { type: "number", nullable: true },
                avgQuality: { type: "number", nullable: true },
              },
            },
          },
        },
      },
      responses: {
        200: {
          description: "Updated daily stat",
          content: {
            "application/json": {
              schema: { $ref: "#/components/schemas/DailyStat" },
            },
          },
        },
        404: { description: "Not found" },
      },
    },
    delete: {
      operationId: "deleteAgentStat",
      tags: ["Agents"],
      summary: "Delete daily stat",
      parameters: [
        {
          name: "agentId",
          in: "path",
          required: true,
          schema: { type: "string", format: "uuid" },
        },
        {
          name: "id",
          in: "path",
          required: true,
          schema: { type: "string", format: "uuid" },
        },
      ],
      responses: {
        204: { description: "Deleted" },
        404: { description: "Not found" },
      },
    },
  },
};

const tags = [
  { name: "Agents", description: "Agent CRUD and nested resources" },
];

export const agentsOpenApi: OpenApiFragment = {
  paths,
  schemas,
  tags,
};
