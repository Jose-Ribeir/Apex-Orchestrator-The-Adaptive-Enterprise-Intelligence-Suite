import { Skeleton } from "@ai-router/ui/skeleton";

interface LoadingScreenProps {
  /** Optional label below the skeleton (e.g. "Loading…") */
  label?: string;
  /** Optional class name for the root container */
  className?: string;
}

/**
 * Full-screen loading state. Use for route-level or gate loading (e.g. AgentGate, auth checks).
 */
export function LoadingScreen({
  label = "Loading…",
  className,
}: LoadingScreenProps) {
  return (
    <div
      className={
        className ??
        "flex min-h-screen flex-col items-center justify-center gap-4 bg-background"
      }
    >
      <div className="flex flex-col items-center gap-2">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-4 w-32" />
      </div>
      <p className="text-muted-foreground text-sm">{label}</p>
    </div>
  );
}
