import { AgentGate } from "@/components/agent-gate";
import { AppSidebar } from "@/components/app-sidebar";
import { LoadingScreen } from "@/components/loading-screen";
import { useSession } from "@/providers/session";
import { Separator } from "@ai-router/ui/separator";
import {
  SidebarInset,
  SidebarProvider,
  SidebarTrigger,
} from "@ai-router/ui/sidebar";
import { Navigate, Outlet } from "react-router-dom";

export function AppLayout() {
  const { data: session, isPending } = useSession();

  if (isPending) return <LoadingScreen />;
  if (!session) return <Navigate to="/auth/sign-in" replace />;

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
            <Outlet />
          </main>
        </SidebarInset>
      </SidebarProvider>
    </AgentGate>
  );
}
