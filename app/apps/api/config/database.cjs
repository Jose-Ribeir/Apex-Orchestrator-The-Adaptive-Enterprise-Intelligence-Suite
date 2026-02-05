require("dotenv/config");

const defaultUrl =
  process.env.DATABASE_URL ||
  "postgresql://postgres:postgres@localhost:5432/ai_router";

module.exports = {
  development: {
    url: defaultUrl,
    dialect: "postgres",
    logging: process.env.SQL_LOGGING === "true" ? console.log : false,
  },
  test: {
    url:
      process.env.DATABASE_URL ||
      "postgresql://postgres:postgres@localhost:5432/ai_router_test",
    dialect: "postgres",
    logging: false,
  },
  production: {
    url: process.env.DATABASE_URL,
    dialect: "postgres",
    logging: false,
    dialectOptions:
      process.env.DATABASE_SSL === "true"
        ? { ssl: { require: true } }
        : {},
  },
};
