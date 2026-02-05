import { redirect } from "next/navigation";
import { getSession } from "@/lib/session";
import { AgentGate } from "@/components/agent-gate";
import { AppSidebar } from "@/components/app-sidebar";
import {
  SidebarInset,
  SidebarProvider,
  SidebarTrigger,
} from "@ai-router/ui/sidebar";
import { Separator } from "@ai-router/ui/separator";

export default async function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const session = await getSession();
  if (!session) {
    redirect("/auth/sign-in");
  }
  return (
    <AgentGate>
      <SidebarProvider>
        <AppSidebar />
        <SidebarInset>
          <header className="relative z-10 flex h-16 shrink-0 items-center gap-2 border-b border-border bg-background px-4 transition-[width,height] ease-linear group-has-[[data-collapsible=icon]]/sidebar-wrapper:h-12">
            <SidebarTrigger className="-ml-1 shrink-0" />
            <Separator orientation="vertical" className="mr-2 h-4 shrink-0" />
          </header>
          <main className="flex min-h-0 flex-1 flex-col overflow-auto p-4">
            {children}
          </main>
        </SidebarInset>
      </SidebarProvider>
    </AgentGate>
  );
}
