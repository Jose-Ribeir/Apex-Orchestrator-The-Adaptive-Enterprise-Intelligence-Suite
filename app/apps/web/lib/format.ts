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

const AGENT_MODE_LABELS: Record<string, string> = {
  PERFORMANCE: "Performance",
  EFFICIENCY: "Efficiency",
  BALANCED: "Balanced",
};

/**
 * Human-readable label for agent mode.
 */
export function agentModeLabel(mode: string | undefined): string {
  if (!mode) return "—";
  return AGENT_MODE_LABELS[mode] ?? mode;
}
