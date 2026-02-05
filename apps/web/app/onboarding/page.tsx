"use client";

import { CreateAgentForm } from "@/components/create-agent-form";
import { LoadingScreen } from "@/components/loading-screen";
import { listAgentsOptions } from "@ai-router/client/react-query";
import { Card, CardContent } from "@ai-router/ui/card";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

export default function OnboardingPage() {
  const router = useRouter();
  const { data: agents, isPending } = useQuery(listAgentsOptions({}));

  useEffect(() => {
    if (!isPending && agents?.data?.length && agents.data.length > 0) {
      router.replace("/");
    }
  }, [isPending, agents?.data?.length, router]);

  if (!isPending && agents?.data?.length && agents.data.length > 0) {
    return <LoadingScreen />;
  }

  return (
    <div className="flex min-h-svh flex-col items-center justify-center gap-6 bg-muted/30 p-6">
      <Card className="w-full max-w-md">
        <CardContent className="pt-6">
          <CreateAgentForm
            title="Create your first agent"
            description="You need at least one agent to use the app. Give it a name, optional instructions, and assign tools."
            submitLabel="Create agent"
          />
        </CardContent>
      </Card>
    </div>
  );
}
