import type { Agent } from "@ai-router/client";

export type AgentFormValues = {
  name: string;
  mode: NonNullable<Agent["mode"]>;
  instructionsText: string;
  selectedToolIds: string[];
};

export type AgentFormBody = {
  name: string;
  mode: NonNullable<Agent["mode"]>;
  instructions?: string[];
  tools?: string[];
};

/**
 * Parse form values into the API body shape (name, mode, instructions array, tools).
 */
export function getAgentBodyFromValues(
  values: AgentFormValues,
): AgentFormBody {
  const instructions = values.instructionsText
    .split("\n")
    .map((s) => s.trim())
    .filter(Boolean);
  return {
    name: values.name.trim(),
    mode: values.mode,
    ...(instructions.length > 0 ? { instructions } : {}),
    ...(values.selectedToolIds.length > 0 ? { tools: values.selectedToolIds } : {}),
  };
}

/**
 * Initial form values for create (empty).
 */
export const defaultAgentFormValues: AgentFormValues = {
  name: "",
  mode: "EFFICIENCY",
  instructionsText: "",
  selectedToolIds: [],
};

/**
 * Build form values from an existing agent (for edit).
 */
export function agentToFormValues(agent: Agent): AgentFormValues {
  const instructions = (agent.instructions ?? [])
    .sort((a, b) => (a.order ?? 0) - (b.order ?? 0))
    .map((i) => i.content ?? "")
    .join("\n");
  const selectedToolIds = (agent.tools ?? []).map((t) => t.id ?? "").filter(Boolean);
  return {
    name: agent.name ?? "",
    mode: (agent.mode as NonNullable<Agent["mode"]>) ?? "EFFICIENCY",
    instructionsText: instructions,
    selectedToolIds,
  };
}
