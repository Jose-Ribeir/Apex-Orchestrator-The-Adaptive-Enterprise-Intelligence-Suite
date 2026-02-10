import type { Config, ClientOptions } from "./client";

/**
 * Runtime config for the API client. Used by the generated client.gen.ts.
 * When used in the web app, VITE_API_URL is set by Vite; otherwise falls back to localhost.
 */
export const createClientConfig = (
  override?: Config<ClientOptions>,
): Config<Required<ClientOptions>> => ({
  baseURL:
    (typeof import.meta !== "undefined" &&
      (import.meta as unknown as { env?: { VITE_API_URL?: string } }).env
        ?.VITE_API_URL) ||
    "http://localhost:8000",
  ...override,
});
