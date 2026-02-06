import type { Session } from "@/lib/auth";

export type { Session, User } from "@/lib/auth";

export async function getSession(): Promise<Session | null> {
  const API_BASE_URL = window.__API_BASE_URL__ || import.meta.env.VITE_API_URL;

  try {
    const res = await fetch(`${API_BASE_URL}/auth/get-session`, {
      credentials: "include",
      cache: "no-store",
    });

    if (!res.ok) return null;

    const data = await res.json();
    if (!data?.user) return null;

    return data as Session;
  } catch {
    return null;
  }
}
