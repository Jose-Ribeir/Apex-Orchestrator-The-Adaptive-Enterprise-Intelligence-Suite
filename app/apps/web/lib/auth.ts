/**
 * Auth client for the Python API (POST /auth/login, /auth/register, /auth/logout).
 * Matches the better-auth-like API expected by login/signup forms.
 */

const getBaseUrl = () =>
  (typeof window !== "undefined" &&
    (window as unknown as { __API_BASE_URL__?: string }).__API_BASE_URL__) ||
  (import.meta as unknown as { env?: { VITE_API_URL?: string } }).env
    ?.VITE_API_URL ||
  "http://localhost:4000";

export type User = {
  id: string;
  email: string;
  name: string;
  image?: string | null;
  email_verified?: boolean;
};

export type Session = {
  user: User;
};

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(url, { ...options, credentials: "include" });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error((err as { detail?: string })?.detail ?? res.statusText);
  }
  return res.json();
}

export const authClient = {
  signIn: {
    email: async (
      args: { email: string; password: string },
      opts?: { onSuccess?: () => void; onError?: (ctx: { error?: { message?: string } }) => void },
    ) => {
      try {
        const base = getBaseUrl().replace(/\/$/, "");
        await fetchJson(`${base}/auth/login`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email: args.email, password: args.password }),
        });
        opts?.onSuccess?.();
        return { error: null };
      } catch (e) {
        const err = e instanceof Error ? e : new Error(String(e));
        opts?.onError?.({ error: { message: err.message } });
        return { error: { message: err.message } };
      }
    },
    social: async (args: {
      provider: string;
      callbackURL?: string;
    }): Promise<{ error: { message: string } | null }> => {
      // Redirect to API OAuth flow; backend handles Google
      const base = getBaseUrl().replace(/\/$/, "");
      const url = `${base}/api/connections/oauth/start?connection=google_gmail`;
      window.location.href = url;
      return { error: null };
    },
  },
  signUp: {
    email: async (
      args: { email: string; password: string; name?: string },
      opts?: { onSuccess?: () => void; onError?: (ctx: { error?: { message?: string } }) => void },
    ) => {
      try {
        const base = getBaseUrl().replace(/\/$/, "");
        await fetchJson(`${base}/auth/register`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            email: args.email,
            password: args.password,
            name: args.name ?? "",
          }),
        });
        opts?.onSuccess?.();
        return { error: null };
      } catch (e) {
        const err = e instanceof Error ? e : new Error(String(e));
        opts?.onError?.({ error: { message: err.message } });
        return { error: { message: err.message } };
      }
    },
  },
  signOut: async () => {
    const base = getBaseUrl().replace(/\/$/, "");
    await fetch(`${base}/auth/logout`, {
      method: "POST",
      credentials: "include",
    });
    window.location.href = "/";
  },
};
