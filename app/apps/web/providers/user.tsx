"use client";

import * as React from "react";
import type { User } from "@/lib/auth";
import { useSession } from "@/providers/session";
import { LoadingScreen } from "@/components/loading-screen";

const UserContext = React.createContext<User | null>(null);

/**
 * Provides the current user. Only renders children when session has a user,
 * so useUser() is always defined (User) when used inside this provider.
 * Use inside (app) after SessionProvider.
 */
export function UserProvider({ children }: { children: React.ReactNode }) {
  const { data, isPending } = useSession();
  const user = data?.user ?? null;

  if (isPending || data === undefined) {
    return (
      <LoadingScreen
        className="flex min-h-svh flex-col items-center justify-center gap-4 bg-background"
        label="Loading…"
      />
    );
  }

  if (!user) {
    return null;
  }

  return <UserContext.Provider value={user}>{children}</UserContext.Provider>;
}

/**
 * Returns the current user. Only use inside UserProvider.
 * User is always defined (non-null) when this provider is mounted.
 */
export function useUser(): User {
  const user = React.useContext(UserContext);
  if (!user) {
    throw new Error(
      "useUser must be used within a UserProvider (and only when session has a user)",
    );
  }
  return user;
}
