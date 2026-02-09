"use client";

import { useActiveAgent } from "@/providers/active-agent";
import { Button } from "@ai-router/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@ai-router/ui/card";
import { Textarea } from "@ai-router/ui/textarea";
import { Bot, Send } from "lucide-react";
import * as React from "react";

import { streamChat, type StreamLine } from "./chat-stream";

type Message = { role: "user" | "assistant"; content: string };

export default function Page() {
  const { agentId } = useActiveAgent();
  const [messages, setMessages] = React.useState<Message[]>([]);
  const [input, setInput] = React.useState("");
  const [isStreaming, setIsStreaming] = React.useState(false);

  const messagesEndRef = React.useRef<HTMLDivElement>(null);
  const scrollToBottom = React.useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  React.useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  const handleSubmit = React.useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      const message = input.trim();
      if (!message || !agentId || isStreaming) return;
      setInput("");
      // Single update: add user message and empty assistant message so streamed text has a target
      setMessages((prev) => [
        ...prev,
        { role: "user", content: message },
        { role: "assistant", content: "" },
      ]);
      setIsStreaming(true);
      try {
        await streamChat({
          agentId,
          message,
          onLine(data: StreamLine) {
            // Backend sends NDJSON: first line = router_decision (no text), then text chunks, then is_final
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
    [agentId, input, isStreaming],
  );

  if (!agentId) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-4 p-8">
        <div className="flex size-16 items-center justify-center rounded-full bg-muted">
          <Bot className="size-8 text-muted-foreground" />
        </div>
        <p className="text-center text-muted-foreground">
          Select an agent from the sidebar to start chatting.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-1 flex-col gap-4 p-4">
      <Card className="flex flex-1 flex-col overflow-hidden">
        <CardHeader className="border-b py-4">
          <CardTitle>Chat</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-1 flex-col gap-4 overflow-hidden p-0">
          <div className="flex-1 space-y-4 overflow-y-auto p-4">
            {messages.length === 0 && (
              <p className="text-center text-sm text-muted-foreground">
                Send a message to start. The agent will use the router and RAG
                when configured.
              </p>
            )}
            {messages.map((msg, i) => (
              <div
                key={i}
                className={
                  msg.role === "user"
                    ? "ml-auto max-w-[85%] rounded-lg bg-primary px-4 py-2 text-primary-foreground"
                    : "mr-auto max-w-[85%] rounded-lg border bg-muted/50 px-4 py-2"
                }
              >
                <p className="whitespace-pre-wrap break-words text-sm">
                  {msg.content || "…"}
                </p>
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>
          <form onSubmit={handleSubmit} className="flex gap-2 border-t p-4">
            <Textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Type a message…"
              className="min-h-[44px] resize-none"
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
              type="submit"
              size="icon"
              disabled={isStreaming || !input.trim()}
              className="shrink-0"
            >
              <Send className="size-4" />
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
