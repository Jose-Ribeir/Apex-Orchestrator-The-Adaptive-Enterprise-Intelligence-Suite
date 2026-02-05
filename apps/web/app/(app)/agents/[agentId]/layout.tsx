"use client";

import { useParams, useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { listAgentsOptions } from "@ai-router/client/react-query";
import type { Agent } from "@ai-router/client";
import { useUser } from "@/providers/user";
import { useEffect } from "react";

export default function AgentIdLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const params = useParams();
  const router = useRouter();
  const agentId = params.agentId as string;
  const user = useUser();

  const { data: agentsData, isPending } = useQuery({
    ...listAgentsOptions({}),
    enabled: Boolean(user?.id),
  });

  const agents = (agentsData as { data?: Agent[] } | undefined)?.data ?? [];
  const agentInList = agents.some((a) => a.id === agentId);

  useEffect(() => {
    if (isPending || !agentId) return;
    if (!agentInList && agents.length > 0) {
      router.replace("/");
    } else if (!agentInList && agents.length === 0) {
      router.replace("/onboarding");
    }
  }, [isPending, agentId, agentInList, agents.length, router]);

  if (!agentInList) {
    return null;
  }

  return <>{children}</>;
}
