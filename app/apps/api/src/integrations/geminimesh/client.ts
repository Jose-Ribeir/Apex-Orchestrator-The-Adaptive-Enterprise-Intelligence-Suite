import { env } from "../../config/env";
import type { AgentConfig, ChatRequest, UpdateAgentRequest } from "./types";

const baseUrl = (): string => env.pythonApiUrl.replace(/\/$/, "");

async function request<T>(
  path: string,
  init: RequestInit & { json?: unknown } & { headers?: Record<string, string> },
): Promise<T> {
  const { json, ...rest } = init;
  const headers: Record<string, string> = {
    ...((init.headers ?? {}) as Record<string, string>),
  };
  if (json !== undefined) {
    headers["Content-Type"] = "application/json";
  }
  const res = await fetch(`${baseUrl()}${path}`, {
    ...rest,
    headers,
    body: json !== undefined ? JSON.stringify(json) : init.body,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`GeminiMesh API ${res.status}: ${text}`);
  }
  const contentType = res.headers.get("content-type");
  if (contentType?.includes("application/json")) {
    return res.json() as Promise<T>;
  }
  return undefined as T;
}

/**
 * GET /health – Health check.
 */
export async function health(): Promise<unknown> {
  return request<unknown>("/health", { method: "GET" });
}

/**
 * POST /update_agent_prompt_geminimesh – Generate prompt and POST to GeminiMesh.
 */
export async function updateAgentPromptGeminimesh(
  body: AgentConfig,
): Promise<unknown> {
  return request<unknown>("/update_agent_prompt_geminimesh", {
    method: "POST",
    json: body,
  });
}

/**
 * POST /optimize_prompt – Standalone prompt optimization (no GeminiMesh call).
 */
export async function optimizePrompt(body: AgentConfig): Promise<unknown> {
  return request<unknown>("/optimize_prompt", {
    method: "POST",
    json: body,
  });
}

/**
 * POST /generate_stream – v6.4: Cheap router → Dynamic generator.
 * Returns a streaming response; caller should read the body stream.
 */
export async function generateStream(body: ChatRequest): Promise<Response> {
  const res = await fetch(`${baseUrl()}/generate_stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`GeminiMesh generate_stream ${res.status}: ${text}`);
  }
  return res;
}

/**
 * POST /update_agent_index – Update agent index.
 */
export async function updateAgentIndex(
  body: UpdateAgentRequest,
): Promise<unknown> {
  return request<unknown>("/update_agent_index", {
    method: "POST",
    json: body,
  });
}

/**
 * POST /upload_and_index – Multipart upload (agent_id + file).
 */
export async function uploadAndIndex(
  agentId: string,
  file: Blob | File,
): Promise<unknown> {
  const form = new FormData();
  form.append("agent_id", agentId);
  form.append("file", file);
  const res = await fetch(`${baseUrl()}/upload_and_index`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`GeminiMesh upload_and_index ${res.status}: ${text}`);
  }
  const contentType = res.headers.get("content-type");
  if (contentType?.includes("application/json")) {
    return res.json();
  }
  return undefined;
}

export const geminimeshClient = {
  health,
  updateAgentPromptGeminimesh,
  optimizePrompt,
  generateStream,
  updateAgentIndex,
  uploadAndIndex,
};
