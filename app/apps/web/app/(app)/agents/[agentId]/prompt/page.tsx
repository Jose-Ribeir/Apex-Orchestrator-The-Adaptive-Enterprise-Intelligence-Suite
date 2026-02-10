import { client } from "@ai-router/client/client.gen";
import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";

type SystemPromptResponse = {
  system_prompt: string;
};

async function fetchAgentSystemPrompt(agentId: string): Promise<string> {
  const response = await client.get({
    url: "/api/agents/{agent_id}/system-prompt",
    path: { agent_id: agentId },
    responseType: "json",
  });
  if ("error" in response && response.error) throw response.error;
  const data = (response as { data?: SystemPromptResponse }).data;
  return data?.system_prompt ?? "";
}

export default function AgentPromptPage() {
  const params = useParams();
  const agentId = params?.agentId as string;

  const { data: systemPrompt, isPending, error } = useQuery({
    queryKey: ["agentSystemPrompt", agentId],
    queryFn: () => fetchAgentSystemPrompt(agentId),
    enabled: Boolean(agentId),
  });

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-1">
        <h1 className="text-2xl font-bold">System prompt</h1>
        <p className="text-muted-foreground text-sm">
          The prompt sent to the model for this agent. Built from name, mode, instructions, and tools. Read-only.
        </p>
      </div>

      {!agentId ? (
        <p className="text-muted-foreground text-sm">No agent selected.</p>
      ) : isPending ? (
        <p className="text-muted-foreground text-sm">Loading…</p>
      ) : error ? (
        <p className="text-destructive text-sm">Failed to load prompt.</p>
      ) : (
        <div className="rounded-xl border border-border/80 bg-card/50 p-4 shadow-sm backdrop-blur-sm">
          <pre className="whitespace-pre-wrap break-words font-mono text-sm text-foreground">
            {systemPrompt ?? ""}
          </pre>
        </div>
      )}
    </div>
  );
}
