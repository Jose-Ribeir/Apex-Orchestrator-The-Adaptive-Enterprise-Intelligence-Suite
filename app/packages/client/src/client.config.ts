import type { CreateClientConfig } from "./client.gen";

export const createClientConfig: CreateClientConfig = (override) => ({
  ...override,
  baseURL: process.env?.API_URL,
});
