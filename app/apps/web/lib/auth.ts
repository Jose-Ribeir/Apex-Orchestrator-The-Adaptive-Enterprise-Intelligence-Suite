export interface User {
  id: string;
  email: string;
  name: string;
  image?: string | null;
  email_verified?: boolean;
}

export interface Session {
  user: User;
}

const API_BASE_URL = window.__API_BASE_URL__ || import.meta.env.VITE_API_URL;

async function apiFetch(path: string, init?: RequestInit) {
  const url = `${API_BASE_URL.replace(/\/$/, "")}${path}`;
  const res = await fetch(url, {
    ...init,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || res.statusText);
  }
  return res.json();
}

export const authClient = {
  signIn: {
    email: async (
      args: { email: string; password: string },
      opts?: {
        onSuccess?: () => void;
        onError?: (ctx: { error?: { message?: string } }) => void;
      },
    ) => {
      try {
        const data = await apiFetch("/auth/login", {
          method: "POST",
          body: JSON.stringify({ email: args.email, password: args.password }),
        });
        opts?.onSuccess?.();
        return { error: null, data };
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Invalid email or password";
        opts?.onError?.({ error: { message } });
        return { error: { message }, data: null };
      }
    },
    // eslint-disable-next-line @typescript-eslint/no-unused-vars -- signature required by better-auth
    social: async (args: { provider: string; callbackURL?: string }) => {
      return {
        error: { message: "Social login not implemented for Python API" },
        data: null,
      };
    },
  },
  signUp: {
    email: async (
      args: { email: string; password: string; name?: string },
      opts?: { onError?: (ctx: { error?: { message?: string } }) => void },
    ) => {
      try {
        await apiFetch("/auth/register", {
          method: "POST",
          body: JSON.stringify({
            email: args.email,
            password: args.password,
            name: args.name ?? "",
          }),
        });
        return { error: null, data: {} };
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Registration failed";
        opts?.onError?.({ error: { message } });
        return { error: { message }, data: null };
      }
    },
  },
  signOut: async () => {
    try {
      await fetch(`${API_BASE_URL.replace(/\/$/, "")}/auth/logout`, {
        method: "POST",
        credentials: "include",
      });
    } catch {
      // ignore
    }
  },
  useSession: () => {
    throw new Error(
      "useSession must be used via SessionProvider from providers/session",
    );
  },
};
