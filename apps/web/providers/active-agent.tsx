"use client";

import * as React from "react";

type ActiveAgentContextValue = {
  agentId: string | null;
  setAgentId: (id: string | null) => void;
};

const ActiveAgentContext = React.createContext<ActiveAgentContextValue | null>(
  null,
);

export function ActiveAgentProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const [agentId, setAgentId] = React.useState<string | null>(null);
  const value = React.useMemo(() => ({ agentId, setAgentId }), [agentId]);
  return (
    <ActiveAgentContext.Provider value={value}>
      {children}
    </ActiveAgentContext.Provider>
  );
}

export function useActiveAgent(): ActiveAgentContextValue {
  const ctx = React.useContext(ActiveAgentContext);
  if (!ctx) {
    throw new Error("useActiveAgent must be used within ActiveAgentProvider");
  }
  return ctx;
}
