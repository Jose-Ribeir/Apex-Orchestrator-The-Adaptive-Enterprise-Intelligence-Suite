import { AgentGate } from "@/components/agent-gate";
import { LoadingScreen } from "@/components/loading-screen";
import { useSession } from "@/providers/session";
import { Navigate, Outlet } from "react-router-dom";

export function OnboardingLayout() {
  const { data: session, isPending } = useSession();

  if (isPending) return <LoadingScreen />;
  if (!session) return <Navigate to="/auth/sign-in" replace />;

  return (
    <AgentGate>
      <Outlet />
    </AgentGate>
  );
}
