import type { AgentInfo } from "@ai-router/client";
import type { CreateAgentRequest, UpdateAgentRequest } from "@ai-router/client";

export type AgentFormValues = {
  name: string;
  mode?: string;
  instructionsText: string;
  selectedToolIds: string[];
  longContextMode?: boolean;
};

type ToolItem = { id?: string; name?: string };

export const defaultAgentFormValues: AgentFormValues = {
  name: "",
  mode: "BALANCED",
  instructionsText: "",
  selectedToolIds: [],
  longContextMode: false,
};

/**
 * Convert AgentInfo (from API) to form values. Accepts AgentInfo with metadata that may have null.
 */
export function agentToFormValues(agent: AgentInfo): AgentFormValues {
  const instructions = agent.instructions ?? [];
  const instructionsText =
    Array.isArray(instructions) ? instructions.join("\n") : "";

  const tools = agent.tools ?? [];
  const selectedToolIds = tools
    .map((t) => (typeof t === "object" && t && "id" in t ? String(t.id) : ""))
    .filter(Boolean);

  return {
    name: agent.name ?? "",
    mode: agent.mode ?? "BALANCED",
    instructionsText,
    selectedToolIds,
    longContextMode: agent.metadata?.long_context_enabled ?? false,
  };
}

export function getAgentBodyFromValues(
  values: AgentFormValues,
  toolsList: ToolItem[],
): CreateAgentRequest | UpdateAgentRequest {
  const toolNames = values.selectedToolIds
    .map((id) => toolsList.find((t) => t.id === id)?.name ?? id)
    .filter(Boolean);

  const instructions = values.instructionsText
    .split("\n")
    .map((s) => s.trim())
    .filter(Boolean);

  return {
    name: values.name.trim(),
    mode: values.mode ?? undefined,
    instructions: instructions.length > 0 ? instructions : undefined,
    tools: toolNames.length > 0 ? toolNames : undefined,
    long_context_mode: values.longContextMode ?? undefined,
  } as CreateAgentRequest | UpdateAgentRequest;
}
