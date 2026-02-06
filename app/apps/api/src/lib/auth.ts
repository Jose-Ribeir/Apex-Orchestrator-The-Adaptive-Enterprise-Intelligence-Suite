import bcrypt from "bcrypt";
import { betterAuth } from "better-auth";
import { openAPI } from "better-auth/plugins";
import { Pool } from "pg";
import { env } from "../config/env";

const pool = new Pool({
  connectionString: env.databaseUrl,
});

export const auth = betterAuth({
  database: pool,
  basePath: "/auth",
  baseURL: env.betterAuthUrl,
  secret: env.betterAuthSecret,
  advanced: {
    disableOriginCheck: true,
    disableCSRFCheck: true,
    defaultCookieAttributes: {
      sameSite: "none",
      secure: true,
    },
  },
  emailAndPassword: {
    enabled: true,
    password: {
      hash: async (password) => bcrypt.hash(password, 10),
      verify: async ({ password, hash }) => {
        if (!hash || typeof hash !== "string") return false;
        if (!hash.startsWith("$2")) return false;
        return bcrypt.compare(password, hash);
      },
    },
  },
  socialProviders: {
    google: {
      clientId: env.googleClientId,
      clientSecret: env.googleClientSecret,
      accessType: "offline",
      prompt: "select_account consent",
    },
  },
  plugins: [
    openAPI({
      path: "/reference",
    }),
  ],
});
