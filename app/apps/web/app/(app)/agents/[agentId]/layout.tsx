import { useUser } from "@/providers/user";
import type { AgentInfo } from "@ai-router/client";
import { listAgentsOptions } from "@ai-router/client/react-query";
import { useQuery } from "@tanstack/react-query";
import { useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";

export default function AgentIdLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const params = useParams();
  const navigate = useNavigate();
  const agentId = params.agentId as string;
  const user = useUser();

  const { data: agentsData, isPending } = useQuery({
    ...listAgentsOptions({}),
    enabled: Boolean(user?.id),
  });

  const agents =
    (agentsData as { agents?: AgentInfo[] } | undefined)?.agents ?? [];
  const agentInList = agents.some((a) => a.agent_id === agentId);

  useEffect(() => {
    if (isPending || !agentId) return;
    if (!agentInList && agents.length > 0) {
      navigate("/", { replace: true });
    } else if (!agentInList && agents.length === 0) {
      navigate("/onboarding", { replace: true });
    }
  }, [isPending, agentId, agentInList, agents.length, navigate]);

  if (!agentInList) {
    return null;
  }

  return <>{children}</>;
}
