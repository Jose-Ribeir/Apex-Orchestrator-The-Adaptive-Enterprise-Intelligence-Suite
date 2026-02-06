import { createAuthClient } from "better-auth/react";

// Browser: from EnvScript (window.__API_BASE_URL__). Server: API_URL.
const baseURL =
  typeof window !== "undefined"
    ? ((window as Window & { __API_BASE_URL__?: string }).__API_BASE_URL__ ??
      "")
    : (process.env.API_URL ?? "");

export const authClient = createAuthClient({
  baseURL,
  basePath: "/auth",
  fetchOptions: {
    credentials: "include",
  },
});

export type Session = (typeof authClient)["$Infer"]["Session"];
export type User = Session["user"];
