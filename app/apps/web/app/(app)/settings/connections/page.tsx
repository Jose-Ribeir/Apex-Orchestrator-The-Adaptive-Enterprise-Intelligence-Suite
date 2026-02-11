"use client";

import type { ConnectionItem } from "@ai-router/client";
import {
  disconnectUserConnectionMutation,
  listConnectionsOptions,
  listConnectionsQueryKey,
} from "@ai-router/client/react-query";
import { Button } from "@ai-router/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@ai-router/ui/card";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link2, Loader2 } from "lucide-react";
import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

function getApiBase(): string {
  return (
    (typeof window !== "undefined" &&
      (window as unknown as { __API_BASE_URL__?: string }).__API_BASE_URL__) ||
    (import.meta as unknown as { env?: { VITE_API_URL?: string } }).env
      ?.VITE_API_URL ||
    ""
  ).replace(/\/$/, "");
}

export default function ConnectionsPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [message, setMessage] = useState<{
    type: "success" | "error";
    text: string;
  } | null>(null);

  const { data, isPending, error } = useQuery(listConnectionsOptions({}));
  const listData = data as { data?: ConnectionItem[] } | undefined;
  const connections: ConnectionItem[] = listData?.data ?? [];

  const disconnectMutation = useMutation({
    ...disconnectUserConnectionMutation(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: listConnectionsQueryKey({}) });
    },
    onError: () => {
      setMessage({ type: "error", text: "Failed to disconnect." });
    },
  });

  useEffect(() => {
    const connected = searchParams.get("connected");
    const err = searchParams.get("error");
    if (connected) {
      setMessage({
        type: "success",
        text: `Connected to ${connected} successfully.`,
      });
      navigate("/settings/connections", { replace: true });
    } else if (err) {
      setMessage({
        type: "error",
        text:
          err === "invalid_state"
            ? "Connection was cancelled or expired."
            : "Connection failed. Please try again.",
      });
      navigate("/settings/connections", { replace: true });
    }
  }, [searchParams, navigate]);

  function handleConnect(providerKey: string) {
    const apiBase = getApiBase();
    const url = `${apiBase}/api/connections/oauth/start?connection=${encodeURIComponent(providerKey)}`;
    window.location.href = url;
  }

  function handleDisconnect(userConnectionId: string) {
    disconnectMutation.mutate({
      path: { user_connection_id: userConnectionId },
    });
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-1">
        <h1 className="text-2xl font-bold">Connections</h1>
        <p className="text-muted-foreground">
          Connect your account to external services. Connected integrations can
          be used by your agents.
        </p>
      </div>

      {message && (
        <div
          className={
            message.type === "success"
              ? "rounded-md border border-green-200 bg-green-50 p-3 text-sm text-green-800 dark:border-green-800 dark:bg-green-950/30 dark:text-green-200"
              : "rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-800 dark:border-red-800 dark:bg-red-950/30 dark:text-red-200"
          }
        >
          {message.text}
        </div>
      )}

      {isPending && (
        <div className="flex items-center gap-2 text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          Loading connections…
        </div>
      )}

      {error && (
        <p className="text-destructive">
          Failed to load connections. Make sure you are signed in.
        </p>
      )}

      {!isPending && !error && connections.length === 0 && (
        <p className="text-muted-foreground">No connection types available.</p>
      )}

      <div className="grid gap-4 sm:grid-cols-2">
        {connections.map((conn) => (
          <Card key={conn.id}>
            <CardHeader className="flex flex-row items-center gap-3">
              {conn.providerKey === "google_gmail" ? (
                <div
                  className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-[#4285F4]/10"
                  aria-hidden
                >
                  <svg
                    className="h-6 w-6"
                    viewBox="0 0 24 24"
                    fill="none"
                    xmlns="http://www.w3.org/2000/svg"
                  >
                    <path
                      d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                      fill="#4285F4"
                    />
                    <path
                      d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                      fill="#34A853"
                    />
                    <path
                      d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                      fill="#FBBC05"
                    />
                    <path
                      d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                      fill="#EA4335"
                    />
                  </svg>
                </div>
              ) : (
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-muted">
                  <Link2 className="h-5 w-5 text-muted-foreground" />
                </div>
              )}
              <div className="min-w-0 flex-1">
                <CardTitle className="text-base">{conn.name}</CardTitle>
                <CardDescription>
                  {conn.providerKey === "google_gmail"
                    ? "Gmail and Google Workspace"
                    : conn.providerKey}
                </CardDescription>
              </div>
            </CardHeader>
            <CardContent>
              {conn.connected ? (
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-sm text-muted-foreground">
                    Connected
                  </span>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() =>
                      conn.userConnectionId &&
                      handleDisconnect(conn.userConnectionId)
                    }
                    disabled={
                      !conn.userConnectionId || disconnectMutation.isPending
                    }
                  >
                    Disconnect
                  </Button>
                </div>
              ) : (
                <Button
                  size="sm"
                  onClick={() => handleConnect(conn.providerKey)}
                >
                  {conn.providerKey === "google_gmail"
                    ? "Connect with Gmail"
                    : "Connect"}
                </Button>
              )}
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
