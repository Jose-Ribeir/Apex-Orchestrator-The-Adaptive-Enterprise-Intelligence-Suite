import type { AgentInfo } from "@ai-router/client";

export type AgentFormValues = {
  name: string;
  mode: NonNullable<AgentInfo["mode"]>;
  instructionsText: string;
  selectedToolIds: string[];
};

export type AgentFormBody = {
  name: string;
  mode: NonNullable<AgentInfo["mode"]>;
  instructions?: string[];
  tools?: string[];
};

export type ToolItem = { id?: string; name?: string };

/**
 * Parse form values into the API body shape (name, mode, instructions array, tools).
 * API expects tool names; when toolsList is provided, selectedToolIds are mapped to names.
 */
export function getAgentBodyFromValues(
  values: AgentFormValues,
  toolsList?: ToolItem[],
): AgentFormBody {
  const instructions = values.instructionsText
    .split("\n")
    .map((s) => s.trim())
    .filter(Boolean);
  const tools =
    values.selectedToolIds.length > 0
      ? toolsList
        ? values.selectedToolIds
            .map((id) => toolsList.find((t) => t.id === id)?.name)
            .filter((n): n is string => Boolean(n))
        : values.selectedToolIds
      : [];
  return {
    name: values.name.trim(),
    mode: values.mode,
    ...(instructions.length > 0 ? { instructions } : {}),
    ...(tools.length > 0 ? { tools } : {}),
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
export function agentToFormValues(agent: AgentInfo): AgentFormValues {
  const instructions = (agent.instructions ?? []).join("\n");
  const selectedToolIds = (agent.tools ?? [])
    .map((t) => t.id ?? "")
    .filter(Boolean);
  return {
    name: agent.name ?? "",
    mode: (agent.mode as NonNullable<AgentInfo["mode"]>) ?? "EFFICIENCY",
    instructionsText: instructions,
    selectedToolIds,
  };
}
