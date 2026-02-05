"use client";

import * as React from "react";
import { authClient } from "@/lib/auth";
import type { Session } from "@/lib/auth";

type RawSessionValue = ReturnType<typeof authClient.useSession>;

export interface SessionContextValue extends Omit<RawSessionValue, "data"> {
  data: Session | null | undefined;
}

const SessionContext = React.createContext<SessionContextValue | null>(null);

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const raw = authClient.useSession();
  const value: SessionContextValue = {
    ...raw,
    data: raw.data as Session | null | undefined,
  };
  return (
    <SessionContext.Provider value={value}>{children}</SessionContext.Provider>
  );
}

export function useSession(): SessionContextValue {
  const ctx = React.useContext(SessionContext);
  if (!ctx) {
    throw new Error("useSession must be used within a SessionProvider");
  }
  return ctx;
}
