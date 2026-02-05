import { agentService } from "../agents";
import { env } from "../../config/env";

export interface AgentWithInstructions {
  agentId: string;
  mode: "PERFORMANCE" | "EFFICIENCY";
  instructionsText: string;
}

/**
 * Fetches the agent by id and returns its mode plus all instructions
 * joined in order into a single string.
 * @param agentId - Agent UUID
 * @param userId - Optional user id to scope access
 */
export async function getAgentAndInstructions(
  agentId: string,
  userId?: string,
): Promise<AgentWithInstructions> {
  const agent = await agentService.getById(agentId, userId);
  const instructionsText = (agent.instructions ?? [])
    .sort((a, b) => a.order - b.order)
    .map((i) => i.content)
    .join("\n\n");
  return {
    agentId: agent.id,
    mode: agent.mode,
    instructionsText,
  };
}

const PYTHON_STREAM_PATH = "/chat/stream";

/**
 * Sends message and instructions to the Python API and returns the streaming
 * Response. The caller is responsible for reading the body stream and closing it.
 * @param message - User message
 * @param instructions - Agent instructions text
 * @returns Fetch Response with readable body stream
 */
export async function callPythonStream(
  message: string,
  instructions: string,
): Promise<Response> {
  const url = `${env.pythonApiUrl.replace(/\/$/, "")}${PYTHON_STREAM_PATH}`;
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, instructions }),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`Python API error ${res.status}: ${text}`);
  }
  return res;
}
