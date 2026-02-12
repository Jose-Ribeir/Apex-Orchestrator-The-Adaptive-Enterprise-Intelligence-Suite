/**
 * Format date for display (e.g. "Jan 15, 2025")
 */
export function formatDate(
  d: Date | string | number | null | undefined,
): string {
  if (d == null) return "—";
  const date = typeof d === "object" ? d : new Date(d);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

/**
 * Format date and time for display
 */
export function formatDateTime(
  d: Date | string | number | null | undefined,
): string {
  if (d == null) return "—";
  const date = typeof d === "object" ? d : new Date(d);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/**
 * Human-readable label for agent mode
 */
export function agentModeLabel(mode: string | null | undefined): string {
  if (!mode) return "—";
  switch (mode) {
    case "PERFORMANCE":
      return "Performance";
    case "EFFICIENCY":
      return "Efficiency";
    case "BALANCED":
      return "Balanced";
    default:
      return mode;
  }
}
