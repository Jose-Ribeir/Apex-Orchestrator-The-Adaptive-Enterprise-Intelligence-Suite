import type { OpenApiFragment } from "../../openapi/base";

const schemas = {
  PerformanceMetric: {
    type: "object",
    properties: {
      id: { type: "string", format: "uuid" },
      modelQueryId: { type: "string", format: "uuid" },
      tokenUsage: { type: "integer" },
      responseTimeMs: { type: "integer", nullable: true },
      efficiencyScore: { type: "number", nullable: true },
      qualityScore: { type: "number", nullable: true },
      createdAt: { type: "string", format: "date-time" },
      updatedAt: { type: "string", format: "date-time" },
    },
  },
};

const paths = {
  "/api/performance-metrics": {
    post: {
      operationId: "createPerformanceMetric",
      tags: ["Performance Metrics"],
      summary: "Create performance metric",
      requestBody: {
        required: true,
        content: {
          "application/json": {
            schema: {
              type: "object",
              required: ["modelQueryId", "tokenUsage"],
              properties: {
                modelQueryId: { type: "string" },
                tokenUsage: { type: "integer" },
                responseTimeMs: { type: "integer" },
                efficiencyScore: { type: "number" },
                qualityScore: { type: "number" },
              },
            },
          },
        },
      },
      responses: { 201: { description: "Created metric" } },
    },
  },
  "/api/performance-metrics/by-query/{modelQueryId}": {
    get: {
      operationId: "getPerformanceMetricByQueryId",
      tags: ["Performance Metrics"],
      summary: "Get metric by model query ID",
      parameters: [
        {
          name: "modelQueryId",
          in: "path",
          required: true,
          schema: { type: "string" },
        },
      ],
      responses: { 200: { description: "Performance metric" } },
    },
  },
  "/api/performance-metrics/{id}": {
    get: {
      operationId: "getPerformanceMetricById",
      tags: ["Performance Metrics"],
      summary: "Get metric by ID",
      parameters: [
        {
          name: "id",
          in: "path",
          required: true,
          schema: { type: "string" },
        },
      ],
      responses: { 200: { description: "Performance metric" } },
    },
    patch: {
      operationId: "updatePerformanceMetric",
      tags: ["Performance Metrics"],
      summary: "Update metric",
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
                tokenUsage: { type: "integer" },
                responseTimeMs: { type: "integer" },
                efficiencyScore: { type: "number" },
                qualityScore: { type: "number" },
              },
            },
          },
        },
      },
      responses: { 200: { description: "Updated metric" } },
    },
    delete: {
      operationId: "deletePerformanceMetric",
      tags: ["Performance Metrics"],
      summary: "Delete metric",
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

const tags = [
  {
    name: "Performance Metrics",
    description: "Query performance metrics",
  },
];

export const performanceMetricsOpenApi: OpenApiFragment = {
  paths,
  schemas,
  tags,
};
