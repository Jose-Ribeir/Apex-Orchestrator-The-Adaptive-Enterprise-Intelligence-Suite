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
import { Badge } from "@ai-router/ui/badge";
import { useQuery } from "@tanstack/react-query";
import { ChevronDown, ChevronRight, Code } from "lucide-react";
import * as React from "react";
import { useParams } from "react-router-dom";

type FlowLogRequest = { user_query?: string; user_query_len?: number };
type RouterDecision = {
  model_to_use?: string;
  needs_rag?: boolean;
  tools_needed?: string[];
  connections_needed?: string[];
  reason?: string;
  needs_human_review?: boolean;
};
type FlowMetrics = {
  call_count?: number;
  router_model?: string;
  generator_model?: string;
  tools_executed?: string[];
  docs_retrieved?: number;
  total_docs?: number;
  input_chars?: number;
  response_chars?: number;
  total_tokens?: number;
  duration_ms?: number;
};

function MethodBadge({ method }: { method: string | null | undefined }) {
  if (!method) return <span>—</span>;
  const isPro = method.toUpperCase() === "PERFORMANCE";
  return (
    <Badge
      variant={isPro ? "default" : "secondary"}
      className="font-mono text-xs"
    >
      {isPro ? "Pro" : "Flash"}
    </Badge>
  );
}

function RouterDecisionCard({ decision }: { decision: RouterDecision | null | undefined }) {
  if (!decision || Object.keys(decision).length === 0) return null;
  const tools = decision.tools_needed ?? [];
  const connections = decision.connections_needed ?? [];
  const model = decision.model_to_use ?? "—";
  const isPro = /pro/i.test(String(model));
  return (
    <div className="flex flex-col gap-3 rounded-lg border border-border/80 bg-muted/20 p-4">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-muted-foreground text-xs font-medium uppercase">Model</span>
        <Badge variant={isPro ? "default" : "secondary"} className="font-mono text-xs">
          {model}
        </Badge>
        {decision.needs_human_review && (
          <Badge variant="outline" className="text-amber-600 border-amber-500/50">
            Human review
          </Badge>
        )}
      </div>
      <div className="grid gap-2 text-sm sm:grid-cols-2">
        <div>
          <span className="text-muted-foreground">RAG</span>
          <span className="ml-2 font-medium">{decision.needs_rag ? "Yes" : "No"}</span>
        </div>
        {tools.length > 0 && (
          <div>
            <span className="text-muted-foreground">Tools</span>
            <div className="mt-1 flex flex-wrap gap-1">
              {tools.map((t) => (
                <Badge key={t} variant="outline" className="text-xs font-normal">
                  {t}
                </Badge>
              ))}
            </div>
          </div>
        )}
        {connections.length > 0 && (
          <div>
            <span className="text-muted-foreground">Connections</span>
            <div className="mt-1 flex flex-wrap gap-1">
              {connections.map((c) => (
                <Badge key={c} variant="outline" className="text-xs font-normal">
                  {c}
                </Badge>
              ))}
            </div>
          </div>
        )}
      </div>
      {decision.reason && (
        <p className="border-t border-border/60 pt-2 italic text-muted-foreground text-xs">
          {decision.reason}
        </p>
      )}
    </div>
  );
}

function MetricsGrid({ metrics, totalTokens, durationMs }: { metrics: FlowMetrics | null | undefined; totalTokens?: number | null; durationMs?: number | null }) {
  const rows: [string, string | number | undefined][] = [];
  if (metrics?.call_count != null) rows.push(["Call count", String(metrics.call_count)]);
  if (metrics?.router_model) rows.push(["Router model", metrics.router_model]);
  if (metrics?.generator_model) rows.push(["Generator model", metrics.generator_model]);
  if ((metrics?.tools_executed ?? [])?.length > 0) rows.push(["Tools executed", (metrics.tools_executed as string[]).join(", ")]);
  if (metrics?.docs_retrieved != null) rows.push(["Docs retrieved", String(metrics.docs_retrieved)]);
  if (metrics?.total_docs != null) rows.push(["Total docs", String(metrics.total_docs)]);
  if (metrics?.input_chars != null) rows.push(["Input chars", metrics.input_chars.toLocaleString()]);
  if (metrics?.response_chars != null) rows.push(["Response chars", metrics.response_chars.toLocaleString()]);
  if (totalTokens != null) rows.push(["Total tokens", totalTokens.toLocaleString()]);
  if (durationMs != null) rows.push(["Duration", `${durationMs} ms`]);
  if (metrics?.duration_ms != null && durationMs == null) rows.push(["Duration", `${metrics.duration_ms} ms`]);
  if (metrics?.total_tokens != null && totalTokens == null) rows.push(["Total tokens", metrics.total_tokens.toLocaleString()]);
  if (rows.length === 0) return null;
  return (
    <div className="grid gap-x-6 gap-y-1 text-sm sm:grid-cols-2">
      {rows.map(([label, value]) => (
        <div key={label} className="flex justify-between gap-2 border-b border-border/40 py-1">
          <span className="text-muted-foreground">{label}</span>
          <span className="tabular-nums font-medium">{value ?? "—"}</span>
        </div>
      ))}
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
                    <TableCell>
                      <MethodBadge method={q.methodUsed} />
                    </TableCell>
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
                        <div className="flex flex-col gap-5 rounded-md border bg-background p-4 text-sm">
                          <Section
                            title="Request"
                            body={
                              (q.flowLog?.request as FlowLogRequest | undefined)?.user_query ??
                              q.userQuery ??
                              "—"
                            }
                          />
                          <Section
                            title="Response"
                            body={q.modelResponse ?? "—"}
                            mono
                          />
                          <div>
                            <h4 className="mb-2 font-medium text-foreground">Usage & metrics</h4>
                            <MetricsGrid
                              metrics={q.flowLog?.metrics as FlowMetrics | undefined}
                              totalTokens={q.totalTokens}
                              durationMs={q.durationMs}
                            />
                          </div>
                          {(q.flowLog?.router_decision != null) && (
                            <div>
                              <h4 className="mb-2 font-medium text-foreground">Router decision</h4>
                              <RouterDecisionCard decision={q.flowLog.router_decision as RouterDecision} />
                            </div>
                          )}
                          {q.flowLog && (
                            <Collapsible>
                              <CollapsibleTrigger className="inline-flex items-center gap-2 rounded border border-border/80 bg-muted/30 px-3 py-2 text-xs font-medium hover:bg-muted/50">
                                <Code className="h-3.5 w-3.5" />
                                Raw flow log (JSON)
                              </CollapsibleTrigger>
                              <CollapsibleContent>
                                <pre className="mt-2 max-h-64 overflow-auto rounded border bg-muted/50 p-3 font-mono text-xs">
                                  {JSON.stringify(q.flowLog, null, 2)}
                                </pre>
                              </CollapsibleContent>
                            </Collapsible>
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
