"use client";

import { useActiveAgent } from "@/providers/active-agent";
import { getHumanTaskOptions } from "@ai-router/client/react-query";
import { Button } from "@ai-router/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@ai-router/ui/card";
import { Textarea } from "@ai-router/ui/textarea";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { Bot, ChevronDown, ChevronUp, Paperclip, Send, X } from "lucide-react";
import * as React from "react";

import { Link } from "react-router-dom";
import {
  streamChat,
  type ChatAttachmentParam,
  type HumanTaskLine,
  type RouterInfo,
  type StreamLine,
} from "./chat-stream";

type Message = {
  role: "user" | "assistant";
  content: string;
  attachments?: ChatAttachmentParam[];
  routerInfo?: RouterInfo;
};

function fileToAttachment(file: File): Promise<ChatAttachmentParam> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const dataUrl = reader.result as string;
      const base64 = dataUrl.includes(",") ? dataUrl.split(",")[1] : dataUrl;
      resolve({ mimeType: file.type || "application/octet-stream", dataBase64: base64 ?? "" });
    };
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(file);
  });
}

export default function Page() {
  const { agentId } = useActiveAgent();
  const [messages, setMessages] = React.useState<Message[]>([]);
  const [input, setInput] = React.useState("");
  const [attachments, setAttachments] = React.useState<ChatAttachmentParam[]>([]);
  const [isStreaming, setIsStreaming] = React.useState(false);
  const [pendingHumanTask, setPendingHumanTask] = React.useState<HumanTaskLine | null>(null);
  const [collapsedRouterIndices, setCollapsedRouterIndices] = React.useState<Set<number>>(new Set());
  const fileInputRef = React.useRef<HTMLInputElement>(null);

  const toggleRouterCollapsed = React.useCallback((index: number) => {
    setCollapsedRouterIndices((prev) => {
      const next = new Set(prev);
      if (next.has(index)) next.delete(index);
      else next.add(index);
      return next;
    });
  }, []);

  const messagesEndRef = React.useRef<HTMLDivElement>(null);
  const scrollToBottom = React.useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  const { data: resolvedTask } = useQuery({
    ...getHumanTaskOptions({
      path: { task_id: pendingHumanTask?.id ?? "" },
    }),
    enabled: Boolean(pendingHumanTask?.id),
    refetchInterval: 5000,
  });

  React.useEffect(() => {
    if (
      resolvedTask?.status === "RESOLVED" &&
      resolvedTask?.humanResolvedResponse &&
      pendingHumanTask
    ) {
      setMessages((prev) => {
        const next = [...prev];
        const last = next[next.length - 1];
        if (last?.role === "assistant") {
          next[next.length - 1] = {
            ...last,
            content: last.content.trim()
              ? `${last.content}\n\n---\n**Reviewer reply:**\n\n${resolvedTask.humanResolvedResponse}`
              : (resolvedTask.humanResolvedResponse ?? ""),
          };
        }
        return next;
      });
      setPendingHumanTask(null);
    }
  }, [resolvedTask?.status, resolvedTask?.humanResolvedResponse, pendingHumanTask]);

  React.useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  const handleSubmit = React.useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      const message = input.trim();
      if (!message || !agentId || isStreaming) return;
      setInput("");
      const attachmentsToSend = [...attachments];
      setAttachments([]);
      // Single update: add user message (with attachments for display) and empty assistant message
      setMessages((prev) => [
        ...prev,
        { role: "user", content: message, attachments: attachmentsToSend.length ? attachmentsToSend : undefined },
        { role: "assistant", content: "" },
      ]);
      setIsStreaming(true);
      try {
        await streamChat({
          agentId,
          message,
          attachments: attachmentsToSend.length ? attachmentsToSend : undefined,
          onLine(data: StreamLine) {
            if (
              "router_decision" in data &&
              data.router_decision != null &&
              "metrics" in data &&
              data.metrics != null
            ) {
              setMessages((prev) => {
                const next = [...prev];
                const last = next[next.length - 1];
                if (last?.role === "assistant") {
                  next[next.length - 1] = {
                    ...last,
                    routerInfo: {
                      router_decision: data.router_decision as RouterInfo["router_decision"],
                      metrics: data.metrics as RouterInfo["metrics"],
                    },
                  };
                }
                return next;
              });
            }
            if ("text" in data && typeof data.text === "string") {
              setMessages((prev) => {
                const next = [...prev];
                const last = next[next.length - 1];
                if (last?.role === "assistant") {
                  next[next.length - 1] = {
                    ...last,
                    content: last.content + data.text,
                  };
                }
                return next;
              });
            }
            if ("is_final" in data && data.is_final && "metrics" in data && data.metrics) {
              const metrics = data.metrics as Record<string, unknown>;
              const toolsFromFinal =
                (metrics.tools_executed as string[] | undefined) ??
                (metrics.tools_used as string[] | undefined);
              if (toolsFromFinal?.length) {
                setMessages((prev) => {
                  const next = [...prev];
                  const last = next[next.length - 1];
                  if (last?.role === "assistant" && last.routerInfo) {
                    const existing = last.routerInfo.metrics.tools_executed ?? last.routerInfo.router_decision.tools_needed ?? [];
                    const merged = [...new Set([...existing, ...toolsFromFinal])];
                    next[next.length - 1] = {
                      ...last,
                      routerInfo: {
                        ...last.routerInfo,
                        metrics: { ...last.routerInfo.metrics, tools_executed: merged },
                      },
                    };
                  }
                  return next;
                });
              }
            }
            if ("human_task" in data && data.human_task) {
              setPendingHumanTask(data.human_task);
            }
          },
        });
      } catch (err) {
        const errorMessage =
          err instanceof Error ? err.message : "Stream failed";
        setMessages((prev) => {
          const next = [...prev];
          const last = next[next.length - 1];
          if (last?.role === "assistant") {
            next[next.length - 1] = {
              ...last,
              content: last.content
                ? `${last.content}\n\n[Error: ${errorMessage}]`
                : `[Error: ${errorMessage}]`,
            };
          } else {
            next.push({
              role: "assistant",
              content: `[Error: ${errorMessage}]`,
            });
          }
          return next;
        });
      } finally {
        setIsStreaming(false);
      }
    },
    [agentId, input, isStreaming, attachments],
  );

  const onAttachmentClick = React.useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  const onFileChange = React.useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = e.target.files;
      if (!files?.length) return;
      Promise.all(Array.from(files).map(fileToAttachment))
        .then((list) =>
          setAttachments((prev) => [...prev, ...list].slice(0, 5))
        )
        .catch(() => { });
      e.target.value = "";
    },
    []
  );

  const removeAttachment = React.useCallback((index: number) => {
    setAttachments((prev) => prev.filter((_, i) => i !== index));
  }, []);

  if (!agentId) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-4 p-8">
        <motion.div
          className="flex size-16 items-center justify-center rounded-full bg-muted"
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.3 }}
        >
          <Bot className="size-8 text-muted-foreground" />
        </motion.div>
        <motion.p
          className="text-center text-muted-foreground"
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.3, delay: 0.1 }}
        >
          Select an agent from the sidebar to start chatting.
        </motion.p>
      </div>
    );
  }

  const lastMessage = messages[messages.length - 1];
  const showStreamingDots =
    isStreaming &&
    lastMessage?.role === "assistant" &&
    lastMessage.content.length > 0;

  return (
    <div className="flex h-full min-h-0 flex-1 flex-col gap-4 p-4 bg-muted/30">
      <Card className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-xl shadow-sm border">
        <CardHeader className="shrink-0 border-b py-4">
          <CardTitle className="text-base font-medium text-muted-foreground">
            Chat
          </CardTitle>
        </CardHeader>
        <CardContent className="flex min-h-0 flex-1 flex-col overflow-hidden p-0">
          <div
            className="min-h-0 flex-1 space-y-4 overflow-y-auto p-4"
            aria-live="polite"
            aria-label="Chat messages"
          >
            {messages.length === 0 && (
              <motion.p
                className="text-center text-sm text-muted-foreground"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.3 }}
              >
                Send a message to start. The agent will use the router and RAG
                when configured.
              </motion.p>
            )}
            {messages.map((msg, i) => (
              <motion.div
                key={i}
                className={
                  msg.role === "user"
                    ? "ml-auto max-w-[85%] rounded-2xl rounded-br-md border bg-muted/50 shadow-sm px-4 py-2.5"
                    : "mr-auto max-w-[85%] rounded-2xl rounded-bl-md border bg-muted/50 shadow-sm px-4 py-2.5"
                }
                initial={{
                  opacity: 0,
                  x: msg.role === "user" ? 16 : -16,
                }}
                animate={{ opacity: 1, x: 0 }}
                transition={{
                  duration: 0.2,
                  delay:
                    i >= messages.length - 2
                      ? (i - Math.max(0, messages.length - 2)) * 0.04
                      : 0,
                }}
              >
                {msg.role === "assistant" && msg.routerInfo && (() => {
                  const toolsUsed = (msg.routerInfo.metrics.tools_executed ?? msg.routerInfo.router_decision.tools_needed ?? []).length > 0
                    ? (msg.routerInfo.metrics.tools_executed ?? msg.routerInfo.router_decision.tools_needed ?? []).join(", ")
                    : "—";
                  const isCollapsed = collapsedRouterIndices.has(i);
                  return (
                    <div className="mb-2 rounded-md border border-border/60 bg-muted/40 px-2.5 py-1.5 text-xs text-muted-foreground">
                      <div className="flex items-center justify-between gap-2">
                        <span>
                          <strong className="font-medium text-foreground/80">Tools used:</strong>{" "}
                          {toolsUsed}
                        </span>
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          className="h-6 shrink-0 px-1.5 text-muted-foreground hover:text-foreground"
                          onClick={() => toggleRouterCollapsed(i)}
                          aria-label={isCollapsed ? "Show routing details" : "Hide routing details"}
                        >
                          {isCollapsed ? (
                            <ChevronDown className="size-3.5" />
                          ) : (
                            <ChevronUp className="size-3.5" />
                          )}
                        </Button>
                      </div>
                      {!isCollapsed && (
                        <>
                          <div className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-0.5 border-t border-border/40 pt-1.5">
                            {msg.routerInfo.metrics.agent_mode ? (
                              <span>
                                <strong className="font-medium text-foreground/80">Mode:</strong>{" "}
                                {msg.routerInfo.metrics.agent_mode}
                              </span>
                            ) : null}
                            <span>
                              <strong className="font-medium text-foreground/80">Tools available:</strong>{" "}
                              {(msg.routerInfo.metrics.tools_available ?? []).length > 0
                                ? (msg.routerInfo.metrics.tools_available ?? []).join(", ")
                                : "—"}
                            </span>
                            {(msg.routerInfo.metrics.connections_used ?? msg.routerInfo.router_decision.connections_needed ?? []).length > 0 && (
                              <span>
                                <strong className="font-medium text-foreground/80">Connections:</strong>{" "}
                                {(msg.routerInfo.metrics.connections_used ?? msg.routerInfo.router_decision.connections_needed ?? []).join(", ")}
                              </span>
                            )}
                            <span>
                              <strong className="font-medium text-foreground/80">Router:</strong>{" "}
                              {msg.routerInfo.metrics.router_model ?? "—"}
                            </span>
                            <span>
                              <strong className="font-medium text-foreground/80">Model:</strong>{" "}
                              {msg.routerInfo.metrics.generator_model ?? msg.routerInfo.router_decision.model_to_use ?? "—"}
                            </span>
                          </div>
                          {msg.routerInfo.router_decision.reason && (
                            <p className="mt-1 border-t border-border/40 pt-1 italic">
                              {msg.routerInfo.router_decision.reason}
                            </p>
                          )}
                        </>
                      )}
                    </div>
                  );
                })()}
                {msg.role === "user" && msg.attachments?.length ? (
                  <div className="flex flex-col gap-2">
                    {msg.attachments.map((att, j) =>
                      att.mimeType.startsWith("image/") ? (
                        <img
                          key={j}
                          src={`data:${att.mimeType};base64,${att.dataBase64}`}
                          alt=""
                          className="max-h-48 max-w-full rounded-md object-contain"
                        />
                      ) : att.mimeType.startsWith("audio/") ? (
                        <audio
                          key={j}
                          controls
                          className="max-w-full"
                          src={`data:${att.mimeType};base64,${att.dataBase64}`}
                        />
                      ) : att.mimeType === "text/csv" || att.mimeType === "application/csv" ? (
                        <span
                          key={j}
                          className="inline-flex items-center gap-1 rounded-md border bg-muted/50 px-2 py-1.5 text-xs text-muted-foreground"
                        >
                          CSV file
                        </span>
                      ) : null
                    )}
                    {msg.content ? (
                      <p className="whitespace-pre-wrap break-words text-sm leading-relaxed">
                        {msg.content}
                      </p>
                    ) : null}
                  </div>
                ) : (
                  <p className="whitespace-pre-wrap break-words text-sm leading-relaxed">
                    {msg.content || "…"}
                  </p>
                )}
                {showStreamingDots && i === messages.length - 1 && (
                  <span className="inline-flex gap-0.5 ml-0.5 align-middle">
                    <span
                      className="inline-block size-1 rounded-full bg-current opacity-60"
                      style={{
                        animation: "typing-dots 1.4s ease-in-out infinite",
                        animationDelay: "0ms",
                      }}
                    />
                    <span
                      className="inline-block size-1 rounded-full bg-current opacity-60"
                      style={{
                        animation: "typing-dots 1.4s ease-in-out infinite",
                        animationDelay: "200ms",
                      }}
                    />
                    <span
                      className="inline-block size-1 rounded-full bg-current opacity-60"
                      style={{
                        animation: "typing-dots 1.4s ease-in-out infinite",
                        animationDelay: "400ms",
                      }}
                    />
                  </span>
                )}
              </motion.div>
            ))}
            <div ref={messagesEndRef} />
            {pendingHumanTask && (
              <div className="flex items-center justify-between gap-2 rounded-lg border border-amber-500/50 bg-amber-500/10 px-3 py-2 text-sm">
                <span>
                  Approval required: {pendingHumanTask.reason}
                  <Link
                    to="/human-tasks"
                    className="ml-2 font-medium text-amber-700 underline dark:text-amber-400"
                  >
                    Review in Human tasks
                  </Link>
                </span>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => setPendingHumanTask(null)}
                  aria-label="Dismiss"
                >
                  <X className="size-4" />
                </Button>
              </div>
            )}
          </div>
          <form
            onSubmit={handleSubmit}
            className="flex shrink-0 flex-col gap-2 border-t bg-card p-4"
          >
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*,audio/*,.csv,text/csv"
              multiple
              className="hidden"
              aria-hidden
              onChange={onFileChange}
            />
            {attachments.length > 0 && (
              <div className="flex flex-wrap gap-1.5">
                {attachments.map((_, i) => (
                  <span
                    key={i}
                    className="inline-flex items-center gap-1 rounded-md bg-muted px-2 py-1 text-xs"
                  >
                    {i + 1}
                    <button
                      type="button"
                      onClick={() => removeAttachment(i)}
                      className="rounded p-0.5 hover:bg-muted-foreground/20"
                      aria-label="Remove attachment"
                    >
                      <X className="size-3" />
                    </button>
                  </span>
                ))}
              </div>
            )}
            <div className="flex gap-2">
              <Textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Type a message…"
                className="min-h-[44px] resize-none transition-colors duration-200 focus-visible:ring-2"
                rows={1}
                disabled={isStreaming}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    handleSubmit(e as unknown as React.FormEvent);
                  }
                }}
              />
              <Button
                type="button"
                variant="outline"
                size="icon"
                disabled={isStreaming}
                onClick={onAttachmentClick}
                aria-label="Attach image, audio, or CSV"
                className="shrink-0"
              >
                <Paperclip className="size-4" />
              </Button>
              <Button
                type="submit"
                size="icon"
                disabled={isStreaming || !input.trim()}
                className="shrink-0 transition-transform duration-150 hover:scale-105 active:scale-95"
              >
                <Send className="size-4" />
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
