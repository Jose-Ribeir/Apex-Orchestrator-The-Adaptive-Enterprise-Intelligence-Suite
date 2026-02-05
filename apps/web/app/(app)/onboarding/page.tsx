"use client";

import { useRouter } from "next/navigation";
import { Card, CardContent } from "@ai-router/ui/card";
import { CreateAgentForm } from "@/components/create-agent-form";

export default function OnboardingPage() {
  const router = useRouter();

  return (
    <div className="flex min-h-svh flex-col items-center justify-center gap-6 bg-muted/30 p-6">
      <Card className="w-full max-w-md">
        <CardContent className="pt-6">
          <CreateAgentForm
            title="Create your first agent"
            description="You need at least one agent to use the app. Give it a name, optional instructions, and assign tools."
            submitLabel="Create agent"
            onSuccess={() => router.push("/")}
          />
        </CardContent>
      </Card>
    </div>
  );
}
