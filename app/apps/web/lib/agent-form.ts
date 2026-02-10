/**
 * Agent form state and helpers for create/edit agent.
 * Used by create-agent-form, settings agents page, and agent-form-fields.
 */

export interface AgentFormValues {
  name: string;
  mode: "PERFORMANCE" | "EFFICIENCY" | "BALANCED";
  instructionsText: string;
  selectedToolIds: string[];
  longContextMode?: boolean;
  longContextMaxTokens?: number;
}

export const defaultAgentFormValues: AgentFormValues = {
  name: "",
  mode: "EFFICIENCY",
  instructionsText: "",
  selectedToolIds: [],
  longContextMode: false,
  longContextMaxTokens: 1_000_000,
};

type ToolItem = { id?: string; name?: string };

/** Agent from API (list or detail) with optional metadata fields. */
type AgentForForm = {
  name?: string | null;
  mode?: string | null;
  instructions?: string[];
  tools?: Array<{ id?: string; name?: string }>;
  metadata?: {
    long_context_enabled?: boolean;
    long_context_max_tokens?: number;
  } | null;
};

export function agentToFormValues(agent: AgentForForm): AgentFormValues {
  const instructionsText = (agent.instructions ?? []).join("\n");
  const selectedToolIds = (agent.tools ?? []).map((t) => t.id ?? t.name ?? "").filter(Boolean);
  return {
    name: agent.name ?? "",
    mode: (agent.mode as AgentFormValues["mode"]) ?? "EFFICIENCY",
    instructionsText,
    selectedToolIds,
    longContextMode: agent.metadata?.long_context_enabled ?? false,
    longContextMaxTokens: agent.metadata?.long_context_max_tokens ?? 1_000_000,
  };
}

export function getAgentBodyFromValues(
  values: AgentFormValues,
  toolsList: ToolItem[]
): {
  name: string;
  mode: string;
  instructions: string[];
  tools: string[];
  long_context_mode?: boolean;
  long_context_max_tokens?: number;
} {
  const instructions = values.instructionsText
    .split("\n")
    .map((s) => s.trim())
    .filter(Boolean);
  const toolNames = values.selectedToolIds
    .map((id) => toolsList.find((t) => t.id === id || t.name === id)?.name ?? id)
    .filter(Boolean);
  const body: {
    name: string;
    mode: string;
    instructions: string[];
    tools: string[];
    long_context_mode?: boolean;
    long_context_max_tokens?: number;
  } = {
    name: values.name.trim(),
    mode: values.mode,
    instructions,
    tools: toolNames,
  };
  if (values.longContextMode !== undefined) {
    body.long_context_mode = values.longContextMode;
  }
  if (values.longContextMaxTokens !== undefined) {
    body.long_context_max_tokens = values.longContextMaxTokens;
  }
  return body;
}
