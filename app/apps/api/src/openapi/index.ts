import { env } from "../config/env";
import { openApiBase } from "./base";
import { agentsOpenApi } from "../features/agents/openapi";
import { toolsOpenApi } from "../features/tools/openapi";
import { humanTasksOpenApi } from "../features/human-tasks/openapi";
import { performanceMetricsOpenApi } from "../features/performance-metrics/openapi";
import { notificationsOpenApi } from "../features/notifications/openapi";
import { apiTokensOpenApi } from "../features/api-tokens/openapi";
import { chatOpenApi } from "../features/chat/openapi";

const fragments = [
  agentsOpenApi,
  toolsOpenApi,
  humanTasksOpenApi,
  performanceMetricsOpenApi,
  notificationsOpenApi,
  apiTokensOpenApi,
  chatOpenApi,
];

const paths = Object.assign({}, ...fragments.map((f) => f.paths));
const tags = fragments.flatMap((f) => f.tags);
const featureSchemas = Object.assign({}, ...fragments.map((f) => f.schemas));

const baseSpec = {
  ...openApiBase,
  tags,
  components: {
    ...openApiBase.components,
    schemas: {
      ...openApiBase.components.schemas,
      ...featureSchemas,
    },
  },
  paths,
};

/** Default spec with localhost server (for backward compatibility). */
export const openApiSpec = baseSpec;

/** Returns the spec with server URLs so Scalar's server selector works. */
export function getOpenApiSpec(serverUrl: string) {
  const url = serverUrl.replace(/\/$/, "");
  const local = `http://localhost:${env.port}`;
  return {
    ...baseSpec,
    servers: [
      { url, description: "Current host" },
      { url: local, description: "Local" },
    ],
  };
}
