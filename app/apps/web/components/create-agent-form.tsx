"use client";

import { useActiveAgent } from "@/providers/active-agent";
import type { Agent } from "@ai-router/client";
import {
  createAgentMutation,
  listAgentsQueryKey,
  listToolsOptions,
} from "@ai-router/client/react-query";
import { Button } from "@ai-router/ui/button";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bot } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { AgentFormFields } from "@/components/agent-form-fields";
import {
  defaultAgentFormValues,
  getAgentBodyFromValues,
} from "@/lib/agent-form";
import type { Tool } from "@ai-router/client";

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
  const [formValues, setFormValues] = useState(defaultAgentFormValues);

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
    const name = formValues.name.trim();
    if (!name) return;
    const body = getAgentBodyFromValues(formValues);
    createAgent.mutate({ body });
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
      <AgentFormFields
        idPrefix="create-agent"
        value={formValues}
        onChange={(next) => setFormValues((prev) => ({ ...prev, ...next }))}
        toolsList={toolsList}
        disabled={createAgent.isPending}
        nameAutoFocus={showHeader}
      />
      <Button type="submit" disabled={createAgent.isPending}>
        {createAgent.isPending ? "Creating…" : submitLabel}
      </Button>
    </form>
  );
}
