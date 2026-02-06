import { generateStream } from "../../integrations/geminimesh";
import { agentService } from "../agents";

export interface AgentWithInstructions {
  agentId: string;
  mode: "PERFORMANCE" | "EFFICIENCY" | "BALANCED";
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

/**
 * Sends message and system prompt (instructions) to the Python/GeminiMesh API
 * generate_stream. The caller is responsible for reading the body stream and closing it.
 * @param agentId - Agent ID
 * @param message - User message
 * @param systemPrompt - Agent instructions / system prompt text
 * @returns Fetch Response with readable body stream
 */
export async function callPythonStream(
  agentId: string,
  message: string,
  systemPrompt: string,
): Promise<Response> {
  return generateStream({
    agent_id: agentId,
    message,
    system_prompt: systemPrompt,
  });
}
