import { client } from "@ai-router/client/client.gen";
import {
  QueryClient,
  QueryClientProvider as TanStackQueryClientProvider,
} from "@tanstack/react-query";
import { useEffect, useState } from "react";

export function ApiProvider({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    client.setConfig({
      baseURL: window.__API_BASE_URL__ || import.meta.env.VITE_API_URL,
      withCredentials: true,
      headers: { "Content-Type": "application/json" },
    });
    if (client.instance) {
      client.instance.defaults.withCredentials = true;
    }
  }, []);

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
