/**
 * Consume POST /generate_stream as NDJSON.
 * Uses fetch + ReadableStream; calls onLine for each parsed line.
 * Rejects if response is not ok or if the stream contains an error object.
 */

const getBaseUrl = (): string => {
  return (
    (typeof window !== "undefined" &&
      (window as unknown as { __API_BASE_URL__?: string }).__API_BASE_URL__) ||
    (import.meta as unknown as { env?: { VITE_API_URL?: string } }).env
      ?.VITE_API_URL ||
    ""
  );
};

export type HumanTaskLine = {
  id: string;
  model_query_id: string;
  reason: string;
  status: string;
  model_message?: string;
  retrieved_data?: string | null;
};

export type StreamLine =
  | { router_decision?: unknown; metrics?: unknown }
  | { text?: string; metrics?: unknown }
  | { text?: string; is_final?: boolean; metrics?: unknown }
  | { human_task?: HumanTaskLine }
  | { email_action?: unknown }
  | { error?: string; detail?: string };

export interface ChatAttachmentParam {
  mimeType: string;
  dataBase64: string;
}

export interface StreamChatParams {
  agentId: string;
  message: string;
  attachments?: ChatAttachmentParam[];
  onLine?: (data: StreamLine) => void;
}

/**
 * POST /generate_stream with body { agent_id, message, attachments? }, read NDJSON stream, call onLine for each line.
 * Throws if fetch fails or if the first line contains an error.
 */
export async function streamChat({
  agentId,
  message,
  attachments,
  onLine,
}: StreamChatParams): Promise<void> {
  const baseUrl = getBaseUrl();
  const url = `${baseUrl.replace(/\/$/, "")}/generate_stream`;
  const body: Record<string, unknown> = {
    agent_id: agentId,
    message,
  };
  if (attachments?.length) {
    body.attachments = attachments.map((a) => ({
      mime_type: a.mimeType,
      data_base64: a.dataBase64,
    }));
  }
  const res = await fetch(url, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Stream failed: ${res.status} ${text || res.statusText}`);
  }
  const reader = res.body?.getReader();
  if (!reader) throw new Error("No response body");
  const decoder = new TextDecoder();
  let buffer = "";
  let isFirst = true;
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";
    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed) continue;
      try {
        const data = JSON.parse(trimmed) as StreamLine;
        if ("error" in data && data.error) {
          throw new Error((data.detail as string) || (data.error as string));
        }
        if (isFirst && onLine) onLine(data);
        else if (onLine) onLine(data);
        isFirst = false;
      } catch (e) {
        if (e instanceof SyntaxError) continue;
        throw e;
      }
    }
  }
  if (buffer.trim()) {
    try {
      const data = JSON.parse(buffer.trim()) as StreamLine;
      if ("error" in data && data.error) {
        throw new Error((data.detail as string) || (data.error as string));
      }
      if (onLine) onLine(data);
    } catch (e) {
      if (!(e instanceof SyntaxError)) throw e;
    }
  }
}
