import { formatDate } from "@/lib/format";
import { listAgentStatsOptions } from "@ai-router/client/react-query";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@ai-router/ui/table";
import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";

export default function AgentStatsPage() {
  const params = useParams();
  const agentId = params?.agentId as string;
  const days = 30;

  const { data: response, isPending } = useQuery({
    ...listAgentStatsOptions({
      path: { agent_id: agentId },
      query: { days },
    }),
    enabled: Boolean(agentId),
  });

  const stats =
    (
      response as
        | {
            data?: Array<{
              id: string;
              date: string;
              totalQueries?: number;
              totalTokens?: number | null;
              avgEfficiency?: number | null;
              avgQuality?: number | null;
            }>;
          }
        | undefined
    )?.data ?? [];

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-1">
        <h1 className="text-2xl font-bold">Daily stats</h1>
        <p className="text-muted-foreground">
          Daily aggregates for this agent.
        </p>
      </div>

      {!agentId ? (
        <p className="text-muted-foreground text-sm">No agent selected.</p>
      ) : isPending ? (
        <p className="text-muted-foreground text-sm">Loading…</p>
      ) : stats.length === 0 ? (
        <p className="text-muted-foreground text-sm">
          No stats for the last {days} days. Use the agent to generate queries.
        </p>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Date</TableHead>
              <TableHead>Queries</TableHead>
              <TableHead>Tokens</TableHead>
              <TableHead>Avg efficiency</TableHead>
              <TableHead>Avg quality</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {stats.map((s) => (
              <TableRow key={s.id}>
                <TableCell>{formatDate(s.date)}</TableCell>
                <TableCell>{s.totalQueries ?? "—"}</TableCell>
                <TableCell>{s.totalTokens ?? "—"}</TableCell>
                <TableCell>
                  {s.avgEfficiency != null ? s.avgEfficiency.toFixed(2) : "—"}
                </TableCell>
                <TableCell>
                  {s.avgQuality != null ? s.avgQuality.toFixed(2) : "—"}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </div>
  );
}
