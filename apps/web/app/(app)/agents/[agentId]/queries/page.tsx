"use client";

import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { listAgentQueriesOptions } from "@ai-router/client/react-query";
import type { ModelQuery } from "@ai-router/client";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@ai-router/ui/table";

function formatDate(d: Date | string | null | undefined): string {
  if (!d) return "—";
  const date = typeof d === "string" ? new Date(d) : d;
  return date.toLocaleString();
}

export default function AgentQueriesPage() {
  const params = useParams();
  const agentId = params?.agentId as string;

  const { data: response, isPending } = useQuery({
    ...listAgentQueriesOptions({
      path: { agentId },
      query: { page: 1, limit: 50 },
    }),
    enabled: Boolean(agentId),
  });
  const queries: ModelQuery[] =
    (response as { data?: ModelQuery[] } | undefined)?.data ?? [];

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-1">
        <h1 className="text-2xl font-bold">Model queries</h1>
        <p className="text-muted-foreground">Query history for this agent.</p>
      </div>

      {!agentId ? (
        <p className="text-muted-foreground text-sm">No agent selected.</p>
      ) : isPending ? (
        <p className="text-muted-foreground text-sm">Loading…</p>
      ) : queries.length === 0 ? (
        <p className="text-muted-foreground text-sm">No queries yet.</p>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>User query</TableHead>
              <TableHead>Method</TableHead>
              <TableHead>Created</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {queries.map((q) => (
              <TableRow key={q.id}>
                <TableCell className="max-w-md truncate">
                  {q.userQuery ?? "—"}
                </TableCell>
                <TableCell>{q.methodUsed ?? "—"}</TableCell>
                <TableCell>{formatDate(q.createdAt)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </div>
  );
}
