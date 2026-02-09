import { AgentMode } from "@ai-router/client";

/**
 * Format a date for display.
 */
export function formatDate(d: Date | string | null | undefined): string {
  if (!d) return "—";
  const date = typeof d === "string" ? new Date(d) : d;
  return date.toLocaleDateString();
}

/**
 * Format a date with time for display.
 */
export function formatDateTime(d: Date | string | null | undefined): string {
  if (!d) return "—";
  const date = typeof d === "string" ? new Date(d) : d;
  return date.toLocaleString();
}

const AGENT_MODE_LABELS: Record<AgentMode, string> = {
  PERFORMANCE: "Performance",
  EFFICIENCY: "Efficiency",
  BALANCED: "Balanced",
};

/**
 * Human-readable label for agent mode.
 */
export function agentModeLabel(mode: AgentMode | null | undefined): string {
  if (mode == null) return "—";
  return AGENT_MODE_LABELS[mode] ?? mode;
}
