import { AgentGate } from "@/components/agent-gate";
import { getSession } from "@/lib/session";
import { redirect } from "next/navigation";

export default async function OnboardingLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const session = await getSession();
  if (!session) redirect("/auth/sign-in");
  return <AgentGate>{children}</AgentGate>;
}
