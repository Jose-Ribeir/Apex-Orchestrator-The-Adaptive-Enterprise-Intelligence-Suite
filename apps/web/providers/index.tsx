"use client";

import { ActiveAgentProvider } from "@/providers/active-agent";
import { ApiProvider } from "@/providers/api";
import { SessionProvider } from "@/providers/session";
import { ThemeProvider } from "@/providers/theme";
import { TooltipProvider } from "@/providers/tooltip";

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <ThemeProvider>
      <TooltipProvider>
        <ApiProvider>
          <SessionProvider>
            <ActiveAgentProvider>{children}</ActiveAgentProvider>
          </SessionProvider>
        </ApiProvider>
      </TooltipProvider>
    </ThemeProvider>
  );
}
