import { config } from "dotenv";

config();

const getEnv = (key: string, defaultValue: string): string =>
  process.env[key] ?? defaultValue;

export const env = {
  nodeEnv: getEnv("NODE_ENV", "development"),
  port: parseInt(getEnv("PORT", "4200"), 10),
  databaseUrl: getEnv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/ai_router",
  ),
  // eslint-disable-next-line turbo/no-undeclared-env-vars
  sqlLogging: process.env.SQL_LOGGING === "true",
  pythonApiUrl: getEnv("PYTHON_API_URL", "http://localhost:8000"),
  betterAuthSecret: getEnv("BETTER_AUTH_SECRET", ""),
  betterAuthUrl: getEnv("BETTER_AUTH_URL", "http://localhost:4200"),
  appUrl: getEnv("APP_URL", ""),
  googleClientId: getEnv("GOOGLE_CLIENT_ID", ""),
  googleClientSecret: getEnv("GOOGLE_CLIENT_SECRET", ""),
} as const;
