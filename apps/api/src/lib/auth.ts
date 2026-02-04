import { betterAuth } from "better-auth";
import { openAPI } from "better-auth/plugins";
import bcrypt from "bcrypt";
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
  plugins: [
    openAPI({
      path: "/reference",
    }),
  ],
});
