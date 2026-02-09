"use client";

import { useActiveAgent } from "@/providers/active-agent";
import { Button } from "@ai-router/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@ai-router/ui/card";
import { Textarea } from "@ai-router/ui/textarea";
import { motion } from "framer-motion";
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
                    ? "ml-auto max-w-[85%] rounded-2xl rounded-br-md shadow-sm bg-primary px-4 py-2.5 text-primary-foreground"
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
                <p className="whitespace-pre-wrap break-words text-sm leading-relaxed">
                  {msg.content || "…"}
                </p>
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
          </div>
          <form
            onSubmit={handleSubmit}
            className="flex shrink-0 gap-2 border-t bg-card p-4"
          >
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
              type="submit"
              size="icon"
              disabled={isStreaming || !input.trim()}
              className="shrink-0 transition-transform duration-150 hover:scale-105 active:scale-95"
            >
              <Send className="size-4" />
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
