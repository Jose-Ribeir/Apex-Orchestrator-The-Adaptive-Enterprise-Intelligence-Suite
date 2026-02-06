import { createAuthClient } from "better-auth/react";

export const authClient = createAuthClient({
  baseURL: window.__API_BASE_URL__ || import.meta.env.VITE_API_URL,
  basePath: "/auth",
  fetchOptions: {
    credentials: "include",
  },
});

export type Session = (typeof authClient)["$Infer"]["Session"];
export type User = Session["user"];
