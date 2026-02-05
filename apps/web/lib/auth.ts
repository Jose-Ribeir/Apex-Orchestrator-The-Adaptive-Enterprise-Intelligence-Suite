import { createAuthClient } from "better-auth/react";

const apiUrl =
  typeof process.env.NEXT_PUBLIC_API_URL !== "undefined"
    ? process.env.NEXT_PUBLIC_API_URL
    : "http://localhost:4200";

export const authClient = createAuthClient({
  baseURL: `${apiUrl}/auth`,
  fetchOptions: {
    credentials: "include",
  },
});

export type Session = (typeof authClient)["$Infer"]["Session"];
export type User = Session["user"];
