import type { CreateClientConfig } from "./client.gen";

export const createClientConfig: CreateClientConfig = (override) => ({
  ...override,
  baseURL: process.env?.NEXT_PUBLIC_API_URL,
});
