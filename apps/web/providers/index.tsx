"use client";

import { ApiProvider } from "@/providers/api";
import { ActiveAgentProvider } from "@/providers/active-agent";
import { SessionProvider } from "@/providers/session";
import { ThemeProvider } from "@/providers/theme";

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <ThemeProvider>
      <ApiProvider>
        <SessionProvider>
          <ActiveAgentProvider>{children}</ActiveAgentProvider>
        </SessionProvider>
      </ApiProvider>
    </ThemeProvider>
  );
}
