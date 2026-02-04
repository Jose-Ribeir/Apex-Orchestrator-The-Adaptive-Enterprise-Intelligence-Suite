import pg from "pg";
import { Sequelize } from "sequelize";
import { env } from "./env";

/**
 * Creates the database if it does not exist (connects to default "postgres" DB first).
 * Allows the API to start when Postgres is running but the app database was never created.
 */
export async function ensureDatabase(): Promise<void> {
  const url = new URL(env.databaseUrl);
  const dbName = (url.pathname || "/postgres").slice(1) || "postgres";
  if (dbName === "postgres") return;

  const adminUrl = new URL(env.databaseUrl);
  adminUrl.pathname = "/postgres";

  const client = new pg.Client({ connectionString: adminUrl.toString() });
  try {
    await client.connect();
    const {
      rows: [row],
    } = await client.query<{ exists: boolean }>(
      "SELECT 1 AS exists FROM pg_database WHERE datname = $1",
      [dbName],
    );
    if (!row) {
      await client.query(`CREATE DATABASE "${dbName.replace(/"/g, '""')}"`);
      console.log(`Database "${dbName}" created.`);
    }
  } finally {
    await client.end();
  }
}

export const sequelize = new Sequelize(env.databaseUrl, {
  dialect: "postgres",
  logging: env.sqlLogging ? console.log : false,
  define: {
    underscored: true,
    timestamps: true,
    paranoid: false,
    defaultScope: {
      where: { isDeleted: false },
    },
  },
});
