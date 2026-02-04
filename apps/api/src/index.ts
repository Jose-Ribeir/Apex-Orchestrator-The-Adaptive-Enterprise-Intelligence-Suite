import { execSync } from "node:child_process";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import app from "./app";
import { env } from "./config/env";
import { ensureDatabase, sequelize } from "./config/database";
import "./models";

const __dirname = dirname(fileURLToPath(import.meta.url));

async function runMigrations(): Promise<void> {
  const cwd = join(__dirname, "..");
  execSync("npx sequelize-cli db:migrate", {
    cwd,
    stdio: "inherit",
    env: { ...process.env, DATABASE_URL: env.databaseUrl },
  });
}

async function main() {
  try {
    await ensureDatabase();
    await sequelize.authenticate();
    console.log("Database connection established.");
    if (env.nodeEnv === "development") {
      await runMigrations();
    }
  } catch (err) {
    console.error("Unable to connect to the database:", err);
    process.exit(1);
  }

  app.listen(env.port, () => {
    console.log(`API listening on http://localhost:${env.port}`);
    console.log(`API docs (Scalar): http://localhost:${env.port}/docs`);
  });
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
