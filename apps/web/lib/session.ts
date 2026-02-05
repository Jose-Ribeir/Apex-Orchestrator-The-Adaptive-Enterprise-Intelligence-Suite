import type { Session } from "@/lib/auth";
import { headers } from "next/headers";

export type { Session, User } from "@/lib/auth";

/**
 * Get the current session by calling the backend auth API with request cookies.
 */
export async function getSession(): Promise<Session | null> {
  const headersList = await headers();
  const cookie = headersList.get("cookie");

  try {
    const res = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL}/auth/get-session`,
      {
        headers: cookie ? { cookie } : {},
        cache: "no-store",
      },
    );

    if (!res.ok) return null;

    const data = await res.json();
    if (!data?.user) return null;

    return data as Session;
  } catch {
    return null;
  }
}
