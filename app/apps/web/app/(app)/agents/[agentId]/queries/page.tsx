import { formatDateTime } from "@/lib/format";
import type { ModelQueryItem } from "@ai-router/client";
import { listAgentQueriesOptions } from "@ai-router/client/react-query";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@ai-router/ui/collapsible";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@ai-router/ui/table";
import { useQuery } from "@tanstack/react-query";
import { ChevronDown, ChevronRight } from "lucide-react";
import * as React from "react";
import { useParams } from "react-router-dom";

export default function AgentQueriesPage() {
  const params = useParams();
  const agentId = params?.agentId as string;
  const [expandedId, setExpandedId] = React.useState<string | null>(null);

  const { data: response, isPending } = useQuery({
    ...listAgentQueriesOptions({
      path: { agent_id: agentId },
      query: { page: 1, limit: 50 },
    }),
    enabled: Boolean(agentId),
  });

  const queries: ModelQueryItem[] = response?.data ?? [];

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-1">
        <h1 className="text-2xl font-bold">Model queries</h1>
        <p className="text-muted-foreground">
          Query history and full request/response flow for this agent.
        </p>
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
              <TableHead className="w-8" />
              <TableHead>User query</TableHead>
              <TableHead>Method</TableHead>
              <TableHead className="text-right">Tokens</TableHead>
              <TableHead className="text-right">Duration</TableHead>
              <TableHead>Created</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {queries.map((q) => (
              <Collapsible
                key={q.id}
                open={expandedId === q.id}
                onOpenChange={(open) =>
                  setExpandedId(open ? (q.id ?? null) : null)
                }
                asChild
              >
                <>
                  <TableRow
                    className={expandedId === q.id ? "border-b-0" : undefined}
                  >
                    <TableCell className="w-8 p-1">
                      <CollapsibleTrigger asChild>
                        <button
                          type="button"
                          className="rounded p-1 hover:bg-muted"
                          aria-label={
                            expandedId === q.id ? "Collapse" : "Expand flow"
                          }
                        >
                          {expandedId === q.id ? (
                            <ChevronDown className="h-4 w-4" />
                          ) : (
                            <ChevronRight className="h-4 w-4" />
                          )}
                        </button>
                      </CollapsibleTrigger>
                    </TableCell>
                    <TableCell className="max-w-md truncate">
                      {q.userQuery ?? "—"}
                    </TableCell>
                    <TableCell>{q.methodUsed ?? "—"}</TableCell>
                    <TableCell className="text-right tabular-nums">
                      {q.totalTokens != null
                        ? q.totalTokens.toLocaleString()
                        : "—"}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {q.durationMs != null ? `${q.durationMs} ms` : "—"}
                    </TableCell>
                    <TableCell>
                      {q.createdAt ? formatDateTime(q.createdAt) : "—"}
                    </TableCell>
                  </TableRow>
                  <CollapsibleContent asChild>
                    <TableRow className="hover:bg-transparent">
                      <TableCell
                        colSpan={6}
                        className="bg-muted/30 p-4 align-top"
                      >
                        <div className="flex flex-col gap-4 rounded-md border bg-background p-4 text-sm">
                          <Section
                            title="Request"
                            body={
                              (
                                q.flowLog?.request as
                                  | { user_query?: string }
                                  | undefined
                              )?.user_query ??
                              q.userQuery ??
                              "—"
                            }
                          />
                          <Section
                            title="Response"
                            body={q.modelResponse ?? "—"}
                            mono
                          />
                          {(q.totalTokens != null ||
                            q.durationMs != null ||
                            q.flowLog?.metrics) && (
                            <div className="flex flex-wrap gap-4 text-sm">
                              {q.totalTokens != null && (
                                <span className="tabular-nums">
                                  <strong>Tokens:</strong>{" "}
                                  {q.totalTokens.toLocaleString()}
                                </span>
                              )}
                              {q.durationMs != null && (
                                <span className="tabular-nums">
                                  <strong>Duration:</strong> {q.durationMs} ms
                                </span>
                              )}
                              {(
                                q.flowLog?.metrics as
                                  | { input_chars?: number }
                                  | undefined
                              )?.input_chars != null && (
                                <span className="tabular-nums">
                                  <strong>Input chars:</strong>{" "}
                                  {(
                                    q.flowLog.metrics as { input_chars: number }
                                  ).input_chars.toLocaleString()}
                                </span>
                              )}
                              {(
                                q.flowLog?.metrics as
                                  | { response_chars?: number }
                                  | undefined
                              )?.response_chars != null && (
                                <span className="tabular-nums">
                                  <strong>Response chars:</strong>{" "}
                                  {(
                                    q.flowLog.metrics as {
                                      response_chars: number;
                                    }
                                  ).response_chars.toLocaleString()}
                                </span>
                              )}
                            </div>
                          )}
                          {q.flowLog && (
                            <>
                              <Section
                                title="Router decision"
                                body={JSON.stringify(
                                  q.flowLog.router_decision ?? {},
                                  null,
                                  2,
                                )}
                                mono
                              />
                              <Section
                                title="Metrics"
                                body={JSON.stringify(
                                  q.flowLog.metrics ?? {},
                                  null,
                                  2,
                                )}
                                mono
                              />
                            </>
                          )}
                        </div>
                      </TableCell>
                    </TableRow>
                  </CollapsibleContent>
                </>
              </Collapsible>
            ))}
          </TableBody>
        </Table>
      )}
    </div>
  );
}

function Section({
  title,
  body,
  mono,
}: {
  title: string;
  body: string;
  mono?: boolean;
}) {
  const [showAll, setShowAll] = React.useState(false);
  const truncateAt = 800;
  const isLong = body.length > truncateAt;
  const display = isLong && !showAll ? body.slice(0, truncateAt) + "…" : body;

  return (
    <div className="flex flex-col gap-1">
      <span className="font-medium text-foreground">{title}</span>
      <pre
        className={
          mono
            ? "overflow-x-auto rounded border bg-muted/50 p-3 text-xs"
            : "whitespace-pre-wrap break-words rounded border bg-muted/50 p-3 text-xs"
        }
        style={{ fontFamily: mono ? "var(--font-mono)" : undefined }}
      >
        {display || "—"}
      </pre>
      {isLong && (
        <button
          type="button"
          className="text-primary text-xs underline"
          onClick={() => setShowAll((v) => !v)}
        >
          {showAll ? "Show less" : "Show full"}
        </button>
      )}
    </div>
  );
}
