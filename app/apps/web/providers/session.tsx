"use client";

import type { Session } from "@/lib/auth";
import * as React from "react";

const getBaseUrl = () =>
  (typeof window !== "undefined" &&
    (window as unknown as { __API_BASE_URL__?: string }).__API_BASE_URL__) ||
  import.meta.env.VITE_API_URL ||
  "";

async function fetchSession(): Promise<Session | null> {
  const url = `${getBaseUrl().replace(/\/$/, "")}/auth/me`;
  const res = await fetch(url, { credentials: "include" });
  if (res.status === 401 || !res.ok) return null;
  const user = await res.json();
  return { user };
}

export interface SessionContextValue {
  data: Session | null | undefined;
  isPending: boolean;
  refetch: () => Promise<void>;
}

const SessionContext = React.createContext<SessionContextValue | null>(null);

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const [data, setData] = React.useState<Session | null | undefined>(undefined);
  const [isPending, setIsPending] = React.useState(true);

  const refetch = React.useCallback(async () => {
    setIsPending(true);
    try {
      const session = await fetchSession();
      setData(session);
    } catch {
      setData(null);
    } finally {
      setIsPending(false);
    }
  }, []);

  React.useEffect(() => {
    refetch();
  }, [refetch]);

  const value: SessionContextValue = { data, isPending, refetch };
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
