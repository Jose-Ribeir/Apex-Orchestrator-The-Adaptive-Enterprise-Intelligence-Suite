"use client";

import { formatDateTime } from "@/lib/format";
import {
  getHumanTaskOptions,
  resolveHumanTaskMutation,
} from "@ai-router/client/react-query";
import { Badge } from "@ai-router/ui/badge";
import { Button } from "@ai-router/ui/button";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@ai-router/ui/collapsible";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Check, ChevronDown } from "lucide-react";
import * as React from "react";
import { Link, useParams } from "react-router-dom";

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

export default function HumanTaskDetailPage() {
  const params = useParams();
  const taskId = params?.taskId as string;
  const queryClient = useQueryClient();

  const { data: task, isPending, error } = useQuery({
    ...getHumanTaskOptions({
      path: { task_id: taskId },
    }),
    enabled: Boolean(taskId),
  });

  const resolveTask = useMutation({
    ...resolveHumanTaskMutation(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["listHumanTasks"] });
      queryClient.invalidateQueries({ queryKey: ["getHumanTask"] });
    },
  });

  if (!taskId) {
    return (
      <div className="flex flex-col gap-6">
        <p className="text-muted-foreground text-sm">No task ID provided.</p>
        <Button asChild variant="outline" size="sm">
          <Link to="/human-tasks">
            <ArrowLeft className="mr-2 size-4" />
            Back to human tasks
          </Link>
        </Button>
      </div>
    );
  }

  if (error || (!isPending && !task)) {
    return (
      <div className="flex flex-col gap-6">
        <p className="text-destructive text-sm">Task not found.</p>
        <Button asChild variant="outline" size="sm">
          <Link to="/human-tasks">
            <ArrowLeft className="mr-2 size-4" />
            Back to human tasks
          </Link>
        </Button>
      </div>
    );
  }

  if (isPending || !task) {
    return <p className="text-muted-foreground text-sm">Loading…</p>;
  }

  const flowLog = task.modelQuery?.flowLog as
    | {
        request?: { agent_id?: string; user_query?: string; user_query_len?: number };
        router_decision?: Record<string, unknown>;
        metrics?: Record<string, unknown>;
        response_preview?: string;
        retrieved_documents?: Array<{
          contents?: string;
          score?: number;
          long_context?: boolean;
          total_docs?: number;
        }>;
        prompt_sent_to_model?: string;
      }
    | undefined;

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-1">
        <div className="flex items-center gap-3">
          <Button asChild variant="ghost" size="sm">
            <Link to="/human-tasks" className="flex items-center gap-2">
              <ArrowLeft className="size-4" />
              Back to human tasks
            </Link>
          </Button>
        </div>
        <div className="mt-2 flex flex-wrap items-center justify-between gap-4">
          <h1 className="text-2xl font-bold">Human task</h1>
          <div className="flex items-center gap-2">
            <Badge variant={task.status === "PENDING" ? "default" : "secondary"}>
              {task.status ?? "—"}
            </Badge>
            {task.status === "PENDING" && (
              <Button
                onClick={() =>
                  resolveTask.mutate({
                    path: { task_id: task.id },
                  })
                }
                disabled={resolveTask.isPending}
              >
                {resolveTask.isPending ? (
                  "Resolving…"
                ) : (
                  <>
                    <Check className="mr-2 size-4" />
                    Mark resolved
                  </>
                )}
              </Button>
            )}
          </div>
        </div>
        <p className="text-muted-foreground">
          Full request/response flow including routing decision.
        </p>
      </div>

      <div className="flex flex-col gap-6 rounded-lg border bg-card p-6">
        {/* Status & Reason */}
        <div className="grid gap-6 sm:grid-cols-2">
          <div>
            <span className="text-muted-foreground text-sm">Status</span>
            <p className="font-medium">{task.status ?? "—"}</p>
          </div>
          <div>
            <span className="text-muted-foreground text-sm">Created</span>
            <p>{formatDateTime(task.createdAt)}</p>
          </div>
        </div>

        <Section title="Reason" body={task.reason ?? "—"} />

        <Section title="Model message" body={task.modelMessage ?? "—"} />

        <Section
          title="Retrieved data"
          body={task.retrievedData ?? "—"}
          mono
        />

        {/* Flow log: Request */}
        {flowLog?.request && (
          <Section
            title="Request (from flow)"
            body={
              JSON.stringify(flowLog.request, null, 2) ??
              (flowLog.request?.user_query ?? "—")
            }
            mono
          />
        )}

        {/* Router decision */}
        {flowLog?.router_decision != null && (
          <Section
            title="Router decision"
            body={JSON.stringify(flowLog.router_decision, null, 2)}
            mono
          />
        )}

        {/* Metrics */}
        {flowLog?.metrics != null && (
          <Section
            title="Metrics"
            body={JSON.stringify(flowLog.metrics, null, 2)}
            mono
          />
        )}

        {/* Response preview */}
        {flowLog?.response_preview && (
          <Section
            title="Response preview"
            body={flowLog.response_preview}
            mono
          />
        )}

        {/* Retrieved documents */}
        {(() => {
          const retrievedDocs = flowLog?.retrieved_documents;
          if (!retrievedDocs?.length) return null;
          return (
            <div className="flex flex-col gap-2">
              <span className="font-medium text-foreground">
                Retrieved documents
              </span>
              <ul className="space-y-3">
                {retrievedDocs.map((doc, i) =>
                  doc.long_context ? (
                    <li
                      key={i}
                      className="rounded border bg-muted/50 p-3 text-sm"
                    >
                      Long context: {doc.total_docs ?? "—"} documents used.
                    </li>
                  ) : (
                    <li key={i} className="flex flex-col gap-1">
                      <span className="text-muted-foreground text-xs">
                        {doc.score != null ? `Score: ${doc.score}` : ""}
                      </span>
                      <pre className="max-h-60 overflow-auto whitespace-pre-wrap rounded border bg-muted/50 p-3 text-xs">
                        {doc.contents ?? "—"}
                      </pre>
                    </li>
                  )
                )}
              </ul>
            </div>
          );
        })()}

        {/* Prompt sent to model */}
        {flowLog?.prompt_sent_to_model && (
          <Collapsible>
            <CollapsibleTrigger className="flex w-full items-center justify-between rounded border bg-muted/50 px-3 py-2 text-left text-sm font-medium hover:bg-muted">
              <span>What was sent to the model</span>
              <ChevronDown className="size-4 shrink-0 transition-transform duration-200 [[data-state=open]_&]:rotate-180" />
            </CollapsibleTrigger>
            <CollapsibleContent>
              <pre className="mt-2 max-h-96 overflow-auto whitespace-pre-wrap rounded border bg-muted/30 p-3 font-mono text-xs">
                {flowLog.prompt_sent_to_model}
              </pre>
            </CollapsibleContent>
          </Collapsible>
        )}
      </div>
    </div>
  );
}
