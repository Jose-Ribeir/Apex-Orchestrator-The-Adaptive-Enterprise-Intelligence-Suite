import { apiReference } from "@scalar/express-api-reference";
import { toNodeHandler } from "better-auth/node";
import cors from "cors";
import express from "express";
import helmet from "helmet";
import { env } from "./config/env";
import { agentsRoutes } from "./features/agents";
import { apiTokensRoutes } from "./features/api-tokens";
import { chatRoutes } from "./features/chat";
import { humanTasksRoutes } from "./features/human-tasks";
import { notificationsRoutes } from "./features/notifications";
import { performanceMetricsRoutes } from "./features/performance-metrics";
import { toolsRoutes } from "./features/tools";
import { auth } from "./lib/auth";
import { asyncHandler } from "./middleware/asyncHandler";
import { errorHandler } from "./middleware/errorHandler";
import { requireAuth } from "./middleware/requireAuth";
import { getOpenApiSpec } from "./openapi/spec";
import "./types/express-augment";

const app = express();

app.use(helmet({ contentSecurityPolicy: false }));
app.use(
  cors({
    origin: true,
    credentials: true,
  }),
);

app.all("/auth/{*any}", toNodeHandler(auth) as express.RequestHandler);

// 21mb limit for document ingest (base64 adds ~33% overhead; backend allows 20mb decoded)
app.use(express.json({ limit: "21mb" }));

app.get("/health", (_req, res) => {
  res.json({ status: "ok", timestamp: new Date().toISOString() });
});

app.use("/api", asyncHandler(requireAuth));

app.use("/api/agents", agentsRoutes);
app.use("/api/tools", toolsRoutes);
app.use("/api/human-tasks", humanTasksRoutes);
app.use("/api/performance-metrics", performanceMetricsRoutes);
app.use("/api/notifications", notificationsRoutes);
app.use("/api/api-tokens", apiTokensRoutes);
app.use("/api/chat", chatRoutes);

app.use(
  "/docs",
  (req: express.Request, res: express.Response, next: express.NextFunction) => {
    const base = getServerUrl(req);
    const handler = apiReference({
      theme: "purple",
      sources: [
        { title: "Main API", slug: "main", url: `${base}/openapi.json` },
        { title: "Auth API", slug: "auth", url: `${base}/openapi-auth.json` },
      ],
    }) as express.RequestHandler;
    handler(req, res, next);
  },
);

function getServerUrl(req: express.Request): string {
  const protocol =
    req.get("x-forwarded-proto") ?? (req.secure ? "https" : "http");
  const host =
    req.get("x-forwarded-host") ?? req.get("host") ?? `localhost:${env.port}`;
  return `${protocol}://${host}`;
}

app.get("/openapi.json", (req, res) => {
  res.setHeader("Content-Type", "application/json");
  res.json(getOpenApiSpec(getServerUrl(req)));
});

app.get("/openapi-auth.json", async (_req, res) => {
  try {
    const schema = await auth.api.generateOpenAPISchema();
    res.setHeader("Content-Type", "application/json");
    res.json(schema);
  } catch (err) {
    res.status(500).json({
      error: "Failed to generate Auth OpenAPI schema",
      message: err instanceof Error ? err.message : String(err),
    });
  }
});

app.use(errorHandler);

export default app;
