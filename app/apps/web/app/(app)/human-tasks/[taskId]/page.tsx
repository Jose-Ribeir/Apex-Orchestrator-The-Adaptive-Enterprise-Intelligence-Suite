"use client";

import { formatDateTime } from "@/lib/format";
import {
  getHumanTaskOptions,
  getHumanTaskQueryKey,
  listHumanTasksQueryKey,
  resolveHumanTaskMutation,
} from "@ai-router/client/react-query";
import { Badge } from "@ai-router/ui/badge";
import { Button } from "@ai-router/ui/button";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@ai-router/ui/collapsible";
import { Textarea } from "@ai-router/ui/textarea";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Check, ChevronDown, Paperclip, Send } from "lucide-react";
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

function fileToAttachment(file: File): Promise<{ mime_type: string; data_base64: string }> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const dataUrl = reader.result as string;
      const base64 = dataUrl.includes(",") ? dataUrl.split(",")[1] : dataUrl;
      resolve({
        mime_type: file.type || "application/octet-stream",
        data_base64: base64 ?? "",
      });
    };
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(file);
  });
}

export default function HumanTaskDetailPage() {
  const params = useParams();
  const taskId = params?.taskId as string;
  const queryClient = useQueryClient();
  const [humanMessage, setHumanMessage] = React.useState("");
  const [attachments, setAttachments] = React.useState<File[]>([]);
  const [attachmentPreviewUrls, setAttachmentPreviewUrls] = React.useState<string[]>([]);
  const fileInputRef = React.useRef<HTMLInputElement>(null);

  React.useEffect(() => {
    const urls = attachments.map((f) =>
      f.type.startsWith("image/") ? URL.createObjectURL(f) : ""
    );
    setAttachmentPreviewUrls(urls);
    return () => {
      urls.forEach((u) => u && URL.revokeObjectURL(u));
    };
  }, [attachments]);

  const { data: task, isPending, error } = useQuery({
    ...getHumanTaskOptions({
      path: { task_id: taskId },
    }),
    enabled: Boolean(taskId),
  });

  const resolveTask = useMutation({
    ...resolveHumanTaskMutation(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: listHumanTasksQueryKey({}) });
      queryClient.invalidateQueries({
        queryKey: getHumanTaskQueryKey({ path: { task_id: taskId } }),
      });
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
              <>
                <Button
                  onClick={() =>
                    resolveTask.mutate({
                      path: { task_id: task.id },
                    })
                  }
                  disabled={resolveTask.isPending}
                  variant="outline"
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
              </>
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

        {task.status === "RESOLVED" && task.humanResolvedResponse && (
          <Section
            title="Resolved reply (formatted)"
            body={task.humanResolvedResponse}
          />
        )}

        {task.status === "PENDING" && (
          <div className="flex flex-col gap-3 rounded-lg border bg-muted/30 p-4">
            <span className="font-medium text-foreground">Your response (optional)</span>
            <p className="text-muted-foreground text-sm">
              Add a message and/or attachments. It will be formatted and sent to the user when you resolve.
            </p>
            <Textarea
              placeholder="Your reply to the user…"
              value={humanMessage}
              onChange={(e) => setHumanMessage(e.target.value)}
              className="min-h-[120px]"
            />
            <div className="flex flex-wrap items-center gap-2">
              <input
                ref={fileInputRef}
                type="file"
                multiple
                className="hidden"
                onChange={(e) => {
                  const files = e.target.files ? Array.from(e.target.files) : [];
                  setAttachments((prev) => [...prev, ...files]);
                }}
              />
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => fileInputRef.current?.click()}
              >
                <Paperclip className="mr-2 size-4" />
                Add files
              </Button>
              {attachments.length > 0 && (
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-muted-foreground text-sm">
                    {attachments.length} file(s) selected
                  </span>
                  <div className="flex flex-wrap gap-2">
                    {attachments.map((file, i) =>
                      file.type.startsWith("image/") && attachmentPreviewUrls[i] ? (
                        <img
                          key={i}
                          src={attachmentPreviewUrls[i]}
                          alt=""
                          className="h-16 w-16 rounded border object-cover"
                        />
                      ) : (
                        <span
                          key={i}
                          className="inline-flex items-center rounded border bg-muted/50 px-2 py-1 text-xs"
                        >
                          {file.name || `File ${i + 1}`}
                        </span>
                      )
                    )}
                  </div>
                </div>
              )}
              <Button
                type="button"
                onClick={async () => {
                  const attachmentPayloads = await Promise.all(
                    attachments.map((f) => fileToAttachment(f))
                  );
                  // API accepts body but generated client types have body?: never
                  resolveTask.mutate({
                    path: { task_id: task.id },
                    body: {
                      human_message: humanMessage.trim() || undefined,
                      attachments:
                        attachmentPayloads.length > 0 ? attachmentPayloads : undefined,
                    },
                  } as any);
                  setHumanMessage("");
                  setAttachments([]);
                }}
                disabled={resolveTask.isPending}
              >
                {resolveTask.isPending ? (
                  "Sending…"
                ) : (
                  <>
                    <Send className="mr-2 size-4" />
                    Resolve and send reply
                  </>
                )}
              </Button>
            </div>
          </div>
        )}

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
