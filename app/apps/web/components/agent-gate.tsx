"use client";

import { LoadingScreen } from "@/components/loading-screen";
import { useSession } from "@/providers/session";
import { UserProvider } from "@/providers/user";
import { AgentInfo } from "@ai-router/client";
import { listAgentsOptions } from "@ai-router/client/react-query";
import { useQuery } from "@tanstack/react-query";
import { useEffect } from "react";
import { useLocation, useNavigate } from "react-router-dom";

const LIST_AGENTS_STALE_MS = 30_000;

function useAgentsGate(pathname: string) {
  const navigate = useNavigate();
  const { data } = useSession();
  const userId = data?.user?.id ?? "";
  const isOnboarding = pathname === "/onboarding";

  const {
    data: agentsData,
    isPending,
    isError,
  } = useQuery({
    ...listAgentsOptions({}),
    retry: false,
    staleTime: LIST_AGENTS_STALE_MS,
    enabled: Boolean(userId) && !isOnboarding,
  });

  const agents =
    (agentsData as { agents?: AgentInfo[] } | undefined)?.agents ?? [];
  const hasAgents = agents.length > 0;
  const sessionReady = Boolean(userId);
  const agentsResolved = !isPending && !isError;
  const shouldRedirectToOnboarding =
    !isOnboarding && sessionReady && agentsResolved && !hasAgents;

  useEffect(() => {
    if (!shouldRedirectToOnboarding) return;
    navigate("/onboarding", { replace: true });
  }, [shouldRedirectToOnboarding, navigate]);

  return {
    isOnboarding,
    canShowApp: sessionReady && agentsResolved && hasAgents,
    shouldRedirect: sessionReady && agentsResolved && !hasAgents,
  };
}

export function AgentGate({ children }: { children: React.ReactNode }) {
  const pathname = useLocation().pathname;
  const { isOnboarding, canShowApp, shouldRedirect } = useAgentsGate(pathname);

  if (isOnboarding) return <UserProvider>{children}</UserProvider>;

  if (shouldRedirect) return null;

  if (!canShowApp) return <LoadingScreen />;

  return <UserProvider>{children}</UserProvider>;
}
