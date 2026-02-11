import { formatDate } from "@/lib/format";
import type { AgentStatRow } from "@ai-router/client";
import { listAgentStatsOptions } from "@ai-router/client/react-query";
import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const tooltipStyle = {
  backgroundColor: "var(--card)",
  color: "var(--card-foreground)",
  border: "1px solid var(--border)",
  borderRadius: "12px",
  boxShadow: "0 4px 24px rgba(0,0,0,0.12)",
  padding: "12px 16px",
  fontSize: "13px",
};

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

  const stats: AgentStatRow[] = response?.data ?? [];

  const chartData = [...stats].reverse();

  const hasQueries = chartData.some((s) => (s.totalQueries ?? 0) > 0);
  const hasTokens = chartData.some((s) => (s.totalTokens ?? 0) > 0);
  const hasEfficiency = chartData.some((s) => s.avgEfficiency != null);
  const hasQuality = chartData.some((s) => s.avgQuality != null);

  return (
    <div className="flex flex-col gap-8">
      <div className="flex flex-col gap-1">
        <h1 className="text-2xl font-bold tracking-tight">Daily stats</h1>
        <p className="text-muted-foreground text-sm">
          Usage and performance over the last {days} days.
        </p>
      </div>

      <p className="rounded-lg border border-border/80 bg-muted/30 px-4 py-3 text-muted-foreground text-sm">
        Router uses 1 cheap call + 1 generator call per request. Tokens and flow
        details are stored for each query; see{" "}
        <Link
          to={agentId ? `/agents/${agentId}/router` : "#"}
          className="text-primary underline hover:no-underline"
        >
          Router & usage
        </Link>{" "}
        and{" "}
        <Link
          to={agentId ? `/agents/${agentId}/queries` : "#"}
          className="text-primary underline hover:no-underline"
        >
          Queries
        </Link>
        .
      </p>

      {!agentId ? (
        <p className="text-muted-foreground text-sm">No agent selected.</p>
      ) : isPending ? (
        <p className="text-muted-foreground text-sm">Loading…</p>
      ) : stats.length === 0 ? (
        <p className="text-muted-foreground text-sm">
          No stats yet. Use the agent to generate queries.
        </p>
      ) : (
        <div className="grid gap-6 sm:grid-cols-1 lg:grid-cols-2">
          {hasQueries && (
            <div className="rounded-xl border border-border/80 bg-card/50 p-5 shadow-sm backdrop-blur-sm">
              <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-muted-foreground">
                Queries per day
              </h2>
              <div className="h-[260px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={chartData}
                    margin={{ top: 16, right: 16, left: 0, bottom: 0 }}
                  >
                    <defs>
                      <linearGradient
                        id="barQueries"
                        x1="0"
                        y1="0"
                        x2="0"
                        y2="1"
                      >
                        <stop
                          offset="0%"
                          stopColor="var(--chart-1)"
                          stopOpacity={1}
                        />
                        <stop
                          offset="100%"
                          stopColor="var(--chart-1)"
                          stopOpacity={0.7}
                        />
                      </linearGradient>
                    </defs>
                    <CartesianGrid
                      strokeDasharray="3 3"
                      stroke="var(--border)"
                      vertical={false}
                    />
                    <XAxis
                      dataKey="date"
                      tickFormatter={(d) => formatDate(d)}
                      tick={{ fill: "var(--muted-foreground)", fontSize: 11 }}
                      axisLine={false}
                      tickLine={false}
                    />
                    <YAxis
                      tick={{ fill: "var(--muted-foreground)", fontSize: 11 }}
                      allowDecimals={false}
                      axisLine={false}
                      tickLine={false}
                      width={28}
                    />
                    <Tooltip
                      contentStyle={tooltipStyle}
                      labelFormatter={(d) => formatDate(d)}
                      cursor={{ fill: "var(--muted)", opacity: 0.5, radius: 4 }}
                    />
                    <Bar
                      dataKey="totalQueries"
                      name="Queries"
                      fill="url(#barQueries)"
                      radius={[6, 6, 0, 0]}
                      maxBarSize={48}
                    />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}

          {hasTokens && (
            <div className="rounded-xl border border-border/80 bg-card/50 p-5 shadow-sm backdrop-blur-sm">
              <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-muted-foreground">
                Tokens per day
              </h2>
              <div className="h-[260px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart
                    data={chartData}
                    margin={{ top: 16, right: 16, left: 0, bottom: 0 }}
                  >
                    <defs>
                      <linearGradient
                        id="areaTokens"
                        x1="0"
                        y1="0"
                        x2="0"
                        y2="1"
                      >
                        <stop
                          offset="0%"
                          stopColor="var(--chart-2)"
                          stopOpacity={0.5}
                        />
                        <stop
                          offset="100%"
                          stopColor="var(--chart-2)"
                          stopOpacity={0.05}
                        />
                      </linearGradient>
                    </defs>
                    <CartesianGrid
                      strokeDasharray="3 3"
                      stroke="var(--border)"
                      vertical={false}
                    />
                    <XAxis
                      dataKey="date"
                      tickFormatter={(d) => formatDate(d)}
                      tick={{ fill: "var(--muted-foreground)", fontSize: 11 }}
                      axisLine={false}
                      tickLine={false}
                    />
                    <YAxis
                      tick={{ fill: "var(--muted-foreground)", fontSize: 11 }}
                      tickFormatter={(v) =>
                        v >= 1000 ? `${(v / 1000).toFixed(1)}k` : String(v)
                      }
                      axisLine={false}
                      tickLine={false}
                      width={36}
                    />
                    <Tooltip
                      contentStyle={tooltipStyle}
                      labelFormatter={(d) => formatDate(d)}
                      formatter={(value: number) => [
                        value.toLocaleString(),
                        "Tokens",
                      ]}
                    />
                    <Area
                      type="monotone"
                      dataKey="totalTokens"
                      name="Tokens"
                      stroke="var(--chart-2)"
                      strokeWidth={2.5}
                      fill="url(#areaTokens)"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}

          {hasEfficiency && (
            <div className="rounded-xl border border-border/80 bg-card/50 p-5 shadow-sm backdrop-blur-sm">
              <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-muted-foreground">
                Avg response time
              </h2>
              <div className="h-[260px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart
                    data={chartData}
                    margin={{ top: 16, right: 16, left: 0, bottom: 0 }}
                  >
                    <CartesianGrid
                      strokeDasharray="3 3"
                      stroke="var(--border)"
                      vertical={false}
                    />
                    <XAxis
                      dataKey="date"
                      tickFormatter={(d) => formatDate(d)}
                      tick={{ fill: "var(--muted-foreground)", fontSize: 11 }}
                      axisLine={false}
                      tickLine={false}
                    />
                    <YAxis
                      tick={{ fill: "var(--muted-foreground)", fontSize: 11 }}
                      axisLine={false}
                      tickLine={false}
                      width={40}
                      tickFormatter={(v) => `${v} ms`}
                    />
                    <Tooltip
                      contentStyle={tooltipStyle}
                      labelFormatter={(d) => formatDate(d)}
                      formatter={(value: number) => [
                        `${value.toFixed(0)} ms`,
                        "Avg latency",
                      ]}
                    />
                    <Line
                      type="monotone"
                      dataKey="avgEfficiency"
                      name="Avg latency"
                      stroke="var(--chart-3)"
                      strokeWidth={2.5}
                      dot={{ fill: "var(--chart-3)", r: 4, strokeWidth: 0 }}
                      activeDot={{
                        r: 6,
                        strokeWidth: 2,
                        stroke: "var(--background)",
                      }}
                      connectNulls
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}

          {hasQuality && (
            <div className="rounded-xl border border-border/80 bg-card/50 p-5 shadow-sm backdrop-blur-sm">
              <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-muted-foreground">
                Avg quality score
              </h2>
              <div className="h-[260px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart
                    data={chartData}
                    margin={{ top: 16, right: 16, left: 0, bottom: 0 }}
                  >
                    <CartesianGrid
                      strokeDasharray="3 3"
                      stroke="var(--border)"
                      vertical={false}
                    />
                    <XAxis
                      dataKey="date"
                      tickFormatter={(d) => formatDate(d)}
                      tick={{ fill: "var(--muted-foreground)", fontSize: 11 }}
                      axisLine={false}
                      tickLine={false}
                    />
                    <YAxis
                      tick={{ fill: "var(--muted-foreground)", fontSize: 11 }}
                      domain={[0, 5]}
                      axisLine={false}
                      tickLine={false}
                      width={28}
                    />
                    <Tooltip
                      contentStyle={tooltipStyle}
                      labelFormatter={(d) => formatDate(d)}
                      formatter={(value: number) => [
                        value?.toFixed(2) ?? "—",
                        "Avg quality",
                      ]}
                    />
                    <Line
                      type="monotone"
                      dataKey="avgQuality"
                      name="Avg quality"
                      stroke="var(--chart-4)"
                      strokeWidth={2.5}
                      dot={{ fill: "var(--chart-4)", r: 4, strokeWidth: 0 }}
                      activeDot={{
                        r: 6,
                        strokeWidth: 2,
                        stroke: "var(--background)",
                      }}
                      connectNulls
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
