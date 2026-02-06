import { createAuthClient } from "better-auth/react";

const baseURL =
  typeof window !== "undefined"
    ? window.location.origin
    : process.env.NEXT_PUBLIC_APP_URL ?? "";

export const authClient = createAuthClient({
  baseURL,
  basePath: "/auth",
  fetchOptions: {
    credentials: "include",
  },
});

export type Session = (typeof authClient)["$Infer"]["Session"];
export type User = Session["user"];
