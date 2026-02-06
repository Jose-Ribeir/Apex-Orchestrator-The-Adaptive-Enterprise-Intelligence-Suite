import type { CreateClientConfig } from "./client.gen";

export const createClientConfig: CreateClientConfig = (override) => ({
  ...override,
  baseURL: window.__API_BASE_URL__,
});
