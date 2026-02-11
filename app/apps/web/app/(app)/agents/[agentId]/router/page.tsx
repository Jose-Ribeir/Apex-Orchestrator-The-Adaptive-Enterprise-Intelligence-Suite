"use client";

import { Link, useParams } from "react-router-dom";
import mermaid from "mermaid";
import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Activity, BarChart3, Zap } from "lucide-react";

const getApiBaseUrl = (): string => {
  return (
    (typeof window !== "undefined" &&
      (window as unknown as { __API_BASE_URL__?: string }).__API_BASE_URL__) ||
    (import.meta as unknown as { env?: { VITE_API_URL?: string } }).env?.VITE_API_URL ||
    ""
  ).replace(/\/$/, "");
};

export type RouterSummary = {
  totalQueries: number;
  totalTokens: number | null;
  avgDurationMs: number | null;
  queriesByMethod: Record<string, number>;
};

async function fetchRouterSummary(
  agentId: string,
  days: number
): Promise<RouterSummary> {
  const base = getApiBaseUrl();
  const res = await fetch(
    `${base}/api/agents/${agentId}/router-summary?days=${days}`,
    { credentials: "include" }
  );
  if (!res.ok) throw new Error("Failed to load router summary");
  return res.json() as Promise<RouterSummary>;
}

const MERMAID_DIAGRAM = `
flowchart LR
  UserQuery[User query]
  Router[Router flash]
  Decision[Router decision]
  RAGOrConnections[RAG or connections]
  Generator[Generator flash or pro]
  Response[Response]
  ModelQuery[ModelQuery DB]

  UserQuery --> Router
  Router --> Decision
  Decision --> RAGOrConnections
  RAGOrConnections --> Generator
  Generator --> Response
  Response -->|"total_tokens, flow_log"| ModelQuery
`;

const SUMMARY_DAYS = 30;

export default function AgentRouterPage() {
  const params = useParams();
  const agentId = params?.agentId as string;
  const containerRef = useRef<HTMLDivElement>(null);
  const [diagramError, setDiagramError] = useState<string | null>(null);

  const { data: summary, isPending: summaryPending, error: summaryError } = useQuery({
    queryKey: ["router-summary", agentId, SUMMARY_DAYS],
    queryFn: () => fetchRouterSummary(agentId, SUMMARY_DAYS),
    enabled: Boolean(agentId),
  });

  useEffect(() => {
    if (!containerRef.current || !agentId) return;
    const pre = document.createElement("pre");
    pre.className = "mermaid";
    pre.textContent = MERMAID_DIAGRAM.trim();
    containerRef.current.innerHTML = "";
    containerRef.current.appendChild(pre);

    mermaid
      .run({
        nodes: [pre],
        suppressErrors: true,
      })
      .then(() => {
        setDiagramError(null);
      })
      .catch((err) => {
        setDiagramError(err?.message ?? "Failed to render diagram");
      });
  }, [agentId]);

  const base = `/agents/${agentId}`;

  return (
    <div className="flex flex-col gap-8">
      <div className="flex flex-col gap-1">
        <h1 className="text-2xl font-bold tracking-tight">Router & usage</h1>
        <p className="text-muted-foreground text-sm">
          How the 2-call router works and where usage and tokens are stored.
        </p>
      </div>

      <section className="flex flex-col gap-3">
        <h2 className="text-lg font-semibold">Flow</h2>
        <p className="text-muted-foreground text-sm">
          Each request runs two LLM calls: a cheap router (always
          gemini-3-flash-preview) and a generator (flash or pro based on the
          router). After the response is streamed, one row is written to the
          database with total_tokens, duration_ms, and flow_log.
        </p>
        <div
          ref={containerRef}
          className="min-h-[200px] rounded-xl border border-border/80 bg-card/50 p-5"
        />
        {diagramError && (
          <p className="text-destructive text-sm">{diagramError}</p>
        )}
      </section>

      {agentId && (
        <section className="flex flex-col gap-3">
          <h2 className="text-lg font-semibold">Usage summary (last {SUMMARY_DAYS} days)</h2>
          {summaryPending ? (
            <p className="text-muted-foreground text-sm">Loading…</p>
          ) : summaryError ? (
            <p className="text-muted-foreground text-sm">
              Summary unavailable (database may not be configured).
            </p>
          ) : summary && summary.totalQueries > 0 ? (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <div className="rounded-xl border border-border/80 bg-card/50 p-4 shadow-sm">
                <p className="text-muted-foreground text-xs font-medium uppercase">Total queries</p>
                <p className="mt-1 text-2xl font-semibold tabular-nums">
                  {summary.totalQueries.toLocaleString()}
                </p>
              </div>
              <div className="rounded-xl border border-border/80 bg-card/50 p-4 shadow-sm">
                <p className="text-muted-foreground text-xs font-medium uppercase">Total tokens</p>
                <p className="mt-1 text-2xl font-semibold tabular-nums">
                  {summary.totalTokens != null
                    ? summary.totalTokens.toLocaleString()
                    : "—"}
                </p>
              </div>
              <div className="rounded-xl border border-border/80 bg-card/50 p-4 shadow-sm">
                <p className="flex items-center gap-1.5 text-muted-foreground text-xs font-medium uppercase">
                  <Zap className="h-3.5 w-3.5" /> Flash (EFFICIENCY)
                </p>
                <p className="mt-1 text-2xl font-semibold tabular-nums">
                  {(summary.queriesByMethod?.EFFICIENCY ?? 0).toLocaleString()}
                </p>
              </div>
              <div className="rounded-xl border border-border/80 bg-card/50 p-4 shadow-sm">
                <p className="text-muted-foreground text-xs font-medium uppercase">Pro (PERFORMANCE)</p>
                <p className="mt-1 text-2xl font-semibold tabular-nums">
                  {(summary.queriesByMethod?.PERFORMANCE ?? 0).toLocaleString()}
                </p>
              </div>
            </div>
          ) : summary ? (
            <p className="text-muted-foreground text-sm">No queries in this period yet.</p>
          ) : null}
          {summary?.avgDurationMs != null && summary.totalQueries > 0 && (
            <p className="text-muted-foreground text-sm">
              Average response time: <span className="tabular-nums font-medium">{Math.round(summary.avgDurationMs)} ms</span>
            </p>
          )}
        </section>
      )}

      <section className="flex flex-col gap-3">
        <h2 className="text-lg font-semibold">Savings</h2>
        <div className="flex flex-col gap-2 text-muted-foreground text-sm">
          <p>
            <strong className="text-foreground">2-call design:</strong> One
            small, cheap router call decides how to handle the query; then a
            single generator call (flash or pro) does the work. This avoids
            running a heavy model for every request.
          </p>
          <p>
            <strong className="text-foreground">Router is always flash:</strong>{" "}
            The router is fixed to a fast, low-cost model so routing adds
            minimal latency and cost.
          </p>
          <p>
            <strong className="text-foreground">Generator is flash or pro per
            request:</strong> The router chooses flash for simpler queries and
            pro for complex ones. Storing flow_log per query lets you analyze
            flash vs pro usage and token consumption over time. Each response
            includes call_count: 2 in the flow metrics.
          </p>
        </div>
      </section>

      <section className="flex flex-col gap-3">
        <h2 className="text-lg font-semibold">View usage data</h2>
        <div className="flex flex-wrap gap-4">
          <Link
            to={`${base}/queries`}
            className="inline-flex items-center gap-2 rounded-lg border border-border bg-card px-4 py-2 text-sm font-medium text-foreground hover:bg-muted/50"
          >
            <BarChart3 className="h-4 w-4" />
            View per-query flow and tokens
          </Link>
          <Link
            to={`${base}/stats`}
            className="inline-flex items-center gap-2 rounded-lg border border-border bg-card px-4 py-2 text-sm font-medium text-foreground hover:bg-muted/50"
          >
            <Activity className="h-4 w-4" />
            View daily usage
          </Link>
        </div>
      </section>
    </div>
  );
}
