"use client";

import { useActiveAgent } from "@/providers/active-agent";
import type { Agent, Tool } from "@ai-router/client";
import {
  createAgentMutation,
  listAgentsQueryKey,
  listToolsOptions,
} from "@ai-router/client/react-query";
import { Button } from "@ai-router/ui/button";
import { Field, FieldGroup, FieldLabel } from "@ai-router/ui/field";
import { Input } from "@ai-router/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@ai-router/ui/select";
import { Textarea } from "@ai-router/ui/textarea";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bot } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

export interface CreateAgentFormProps {
  onSuccess?: (agent: Agent) => void;
  title?: string;
  description?: string;
  submitLabel?: string;
  showHeader?: boolean;
}

export function CreateAgentForm({
  onSuccess,
  title = "Create agent",
  description = "Give it a name, optional instructions, and assign tools.",
  submitLabel = "Create agent",
  showHeader = true,
}: CreateAgentFormProps) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { setAgentId } = useActiveAgent();
  const [mode, setMode] = useState<NonNullable<Agent["mode"]>>("EFFICIENCY");
  const [instructionsText, setInstructionsText] = useState("");
  const [selectedToolIds, setSelectedToolIds] = useState<string[]>([]);

  const { data: toolsData } = useQuery(listToolsOptions({}));
  const toolsList = (toolsData as { data?: Tool[] } | undefined)?.data ?? [];

  const createAgent = useMutation({
    ...createAgentMutation(),
    onSuccess: async (created) => {
      if (created?.id) setAgentId(created.id);
      await queryClient.refetchQueries({ queryKey: listAgentsQueryKey({}) });
      onSuccess?.(created as Agent);
      navigate("/");
    },
  });

  function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    const name = (
      form.querySelector<HTMLInputElement>('[name="name"]')?.value ?? ""
    ).trim();
    if (!name) return;
    const instructions = instructionsText
      .split("\n")
      .map((s) => s.trim())
      .filter(Boolean);
    const body = {
      name,
      mode,
      ...(instructions.length > 0 ? { instructions } : {}),
      ...(selectedToolIds.length > 0 ? { tools: selectedToolIds } : {}),
    };
    createAgent.mutate({ body });
  }

  function toggleTool(id: string) {
    setSelectedToolIds((prev) =>
      prev.includes(id) ? prev.filter((t) => t !== id) : [...prev, id],
    );
  }

  return (
    <form onSubmit={onSubmit} className="flex flex-col gap-6">
      {showHeader && (
        <div className="flex flex-col items-center gap-2 text-center">
          <div className="flex size-12 items-center justify-center rounded-full bg-primary/10 text-primary">
            <Bot className="size-6" />
          </div>
          <h2 className="text-2xl font-bold">{title}</h2>
          <p className="text-muted-foreground text-sm">{description}</p>
        </div>
      )}
      {createAgent.error && (
        <p className="text-center text-sm text-destructive" role="alert">
          {(createAgent.error as { message?: string })?.message ??
            "Something went wrong"}
        </p>
      )}
      <FieldGroup>
        <Field>
          <FieldLabel htmlFor="create-agent-name">Agent name</FieldLabel>
          <Input
            id="create-agent-name"
            name="name"
            type="text"
            placeholder="e.g. My Assistant"
            required
            disabled={createAgent.isPending}
            autoFocus={showHeader}
          />
        </Field>
        <Field>
          <FieldLabel htmlFor="create-agent-mode">Mode</FieldLabel>
          <Select
            value={mode}
            onValueChange={(v) => setMode(v as NonNullable<Agent["mode"]>)}
            disabled={createAgent.isPending}
          >
            <SelectTrigger id="create-agent-mode">
              <SelectValue placeholder="Select mode" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="EFFICIENCY">Efficiency</SelectItem>
              <SelectItem value="BALANCED">Balanced</SelectItem>
              <SelectItem value="PERFORMANCE">Performance</SelectItem>
            </SelectContent>
          </Select>
        </Field>
        <Field>
          <FieldLabel htmlFor="create-agent-instructions">
            Instructions
          </FieldLabel>
          <Textarea
            id="create-agent-instructions"
            placeholder="Instruction 1&#10;Instruction 2"
            value={instructionsText}
            onChange={(e) => setInstructionsText(e.target.value)}
            disabled={createAgent.isPending}
            rows={4}
            className="resize-none"
          />
        </Field>
        <Field>
          <FieldLabel>Tools (optional)</FieldLabel>
          <div className="border-input rounded-none border bg-transparent px-2.5 py-2">
            <div className="flex max-h-32 flex-wrap gap-2 overflow-y-auto">
              {toolsList.length === 0 ? (
                <p className="text-muted-foreground text-xs">
                  No tools in catalog yet.
                </p>
              ) : (
                toolsList.map((tool) => (
                  <label
                    key={tool.id}
                    className="text-foreground hover:bg-muted flex cursor-pointer items-center gap-2 rounded px-2 py-1 text-xs"
                  >
                    <input
                      type="checkbox"
                      checked={selectedToolIds.includes(tool.id ?? "")}
                      onChange={() => toggleTool(tool.id ?? "")}
                      disabled={createAgent.isPending}
                      className="rounded border-input"
                    />
                    <span>{tool.name ?? tool.id}</span>
                  </label>
                ))
              )}
            </div>
          </div>
        </Field>
      </FieldGroup>
      <Button type="submit" disabled={createAgent.isPending}>
        {createAgent.isPending ? "Creating…" : submitLabel}
      </Button>
    </form>
  );
}
