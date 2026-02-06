"use client";

import { client } from "@ai-router/client/client.gen";
import {
  QueryClient,
  QueryClientProvider as TanStackQueryClientProvider,
} from "@tanstack/react-query";
import { useState } from "react";

function getApiBaseURL(): string {
  if (typeof window !== "undefined") {
    const runtime = (window as Window & { __API_BASE_URL__?: string })
      .__API_BASE_URL__;
    if (runtime) return runtime;
  }
  return process.env.API_URL ?? "";
}

const apiBaseURL = getApiBaseURL();

client.setConfig({
  baseURL: apiBaseURL,
  withCredentials: true,
  headers: { "Content-Type": "application/json" },
});
if (client.instance) {
  client.instance.defaults.withCredentials = true;
}

export function ApiProvider({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 60 * 1000,
          },
        },
      }),
  );

  return (
    <TanStackQueryClientProvider client={queryClient}>
      {children}
    </TanStackQueryClientProvider>
  );
}
