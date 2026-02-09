"use client";

import { AgentGate } from "@/components/agent-gate";
import { AppSidebar } from "@/components/app-sidebar";
import { CommandPalette } from "@/components/command-palette";
import { LoadingScreen } from "@/components/loading-screen";
import { useSession } from "@/providers/session";
import { Button } from "@ai-router/ui/button";
import { Separator } from "@ai-router/ui/separator";
import {
  SidebarInset,
  SidebarProvider,
  SidebarTrigger,
} from "@ai-router/ui/sidebar";
import { Search } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Navigate, Outlet } from "react-router-dom";

export function AppLayout() {
  const { data: session, isPending } = useSession();
  const [commandOpen, setCommandOpen] = useState(false);

  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setCommandOpen((open) => !open);
      }
    };
    window.addEventListener("keydown", down);
    return () => window.removeEventListener("keydown", down);
  }, []);

  const openCommand = useCallback(() => setCommandOpen(true), []);

  if (isPending) return <LoadingScreen />;
  if (!session) return <Navigate to="/auth/sign-in" replace />;

  return (
    <AgentGate>
      <SidebarProvider className="h-svh overflow-hidden">
        <AppSidebar />
        <SidebarInset className="min-h-0">
          <header className="relative z-10 flex h-16 shrink-0 items-center gap-2 border-b border-border bg-background px-4 transition-[width,height] ease-linear group-has-[[data-collapsible=icon]]/sidebar-wrapper:h-12">
            <SidebarTrigger className="-ml-1 shrink-0" />
            <Separator orientation="vertical" className="mr-2 h-4 shrink-0" />
            <Button
              variant="outline"
              size="sm"
              className="gap-2 text-muted-foreground"
              onClick={openCommand}
            >
              <Search className="size-4" />
              <span className="hidden sm:inline">Search...</span>
              <kbd className="pointer-events-none hidden h-5 select-none items-center gap-1 rounded border bg-muted px-1.5 font-mono text-[10px] font-medium opacity-100 sm:flex">
                <span className="text-xs">⌘</span>K
              </kbd>
            </Button>
          </header>
          <main className="flex min-h-0 flex-1 flex-col overflow-hidden p-4">
            <Outlet />
          </main>
        </SidebarInset>
      </SidebarProvider>
      <CommandPalette open={commandOpen} onOpenChange={setCommandOpen} />
    </AgentGate>
  );
}
