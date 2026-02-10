"use client";

import { AgentFormFields } from "@/components/agent-form-fields";
import {
  agentToFormValues,
  defaultAgentFormValues,
  getAgentBodyFromValues,
} from "@/lib/agent-form";
import { agentModeLabel, formatDate } from "@/lib/format";
import { useActiveAgent } from "@/providers/active-agent";
import type { AgentInfo, AgentMode } from "@ai-router/client";
import { client } from "@ai-router/client/client.gen";
import {
  deleteAgentMutation,
  listAgentsOptions,
  listAgentsQueryKey,
  listToolsOptions,
  updateAgentMutation,
} from "@ai-router/client/react-query";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@ai-router/ui/alert-dialog";
import { Button } from "@ai-router/ui/button";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@ai-router/ui/collapsible";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@ai-router/ui/sheet";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@ai-router/ui/table";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bot, ChevronDown, Pencil, Trash2 } from "lucide-react";
import { useState } from "react";

type SystemPromptResponse = { system_prompt: string };

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

export default function SettingsAgentsPage() {
  const queryClient = useQueryClient();
  const { agentId: activeAgentId, setAgentId } = useActiveAgent();
  const [editAgent, setEditAgent] = useState<AgentInfo | null>(null);
  const [deleteAgent, setDeleteAgent] = useState<AgentInfo | null>(null);

  const { data: data, isPending } = useQuery(listAgentsOptions({}));

  type ToolItem = { id?: string; name?: string };
  const { data: toolsData } = useQuery({
    ...listToolsOptions({}),
    enabled: editAgent != null,
  });
  const toolsList: ToolItem[] =
    (toolsData as { data?: ToolItem[] } | undefined)?.data ?? [];

  const { data: systemPrompt, isPending: systemPromptLoading } = useQuery({
    queryKey: ["agentSystemPrompt", editAgent?.agent_id],
    queryFn: () => fetchAgentSystemPrompt(editAgent!.agent_id),
    enabled: Boolean(editAgent?.agent_id),
  });

  const updateAgent = useMutation({
    ...updateAgentMutation(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: listAgentsQueryKey({}) });
      setEditAgent(null);
    },
  });

  const [editFormValues, setEditFormValues] = useState(defaultAgentFormValues);

  const openEditSheet = (agent: AgentInfo) => {
    setEditAgent(agent);
    setEditFormValues(agentToFormValues(agent));
  };

  const deleteAgentMutationState = useMutation({
    ...deleteAgentMutation(),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: listAgentsQueryKey({}) });
      if (activeAgentId === variables.path.agent_id) {
        setAgentId(null);
      }
      setDeleteAgent(null);
    },
  });

  const handleEditSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!editAgent?.agent_id) return;
    const name = editFormValues.name.trim();
    if (!name) return;
    const body = getAgentBodyFromValues(editFormValues, toolsList);
    updateAgent.mutate({
      path: { agent_id: editAgent.agent_id },
      body,
    });
  };

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-1">
        <h1 className="text-2xl font-bold">Agents</h1>
        <p className="text-muted-foreground">
          Manage all your agents: edit name, mode, instructions, and tools, or
          delete agents.
        </p>
      </div>

      {isPending ? (
        <p className="text-muted-foreground text-sm">Loading agents…</p>
      ) : data?.agents.length === 0 ? (
        <p className="text-muted-foreground text-sm">
          No agents yet. Create one from the agent switcher in the sidebar.
        </p>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Mode</TableHead>
              <TableHead>Updated</TableHead>
              <TableHead className="w-[120px]" />
            </TableRow>
          </TableHeader>
          <TableBody>
            {data?.agents.map((agent) => (
              <TableRow key={agent.agent_id}>
                <TableCell className="font-medium">
                  <span className="flex items-center gap-2">
                    <Bot className="size-4 text-muted-foreground" />
                    {agent.name ?? "—"}
                  </span>
                </TableCell>
                <TableCell>{agentModeLabel(agent.mode as AgentMode)}</TableCell>
                <TableCell>{formatDate(agent.updated_at)}</TableCell>
                <TableCell>
                  <div className="flex items-center gap-1">
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => openEditSheet(agent)}
                      aria-label="Edit agent"
                    >
                      <Pencil className="size-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="text-destructive hover:text-destructive"
                      onClick={() => setDeleteAgent(agent)}
                      disabled={deleteAgentMutationState.isPending}
                      aria-label="Delete agent"
                    >
                      <Trash2 className="size-4" />
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}

      <Sheet
        open={editAgent != null}
        onOpenChange={(o) => !o && setEditAgent(null)}
      >
        <SheetContent side="right" className="w-full max-w-md sm:max-w-md">
          <SheetHeader>
            <SheetTitle>Edit agent</SheetTitle>
          </SheetHeader>
          {editAgent && (
            <form
              onSubmit={handleEditSubmit}
              className="mt-6 flex flex-col gap-4"
            >
              <AgentFormFields
                idPrefix="edit-agent"
                value={editFormValues}
                onChange={(next) =>
                  setEditFormValues((prev) => ({ ...prev, ...next }))
                }
                toolsList={toolsList}
                disabled={updateAgent.isPending}
                nameLabel="Name"
                instructionsLabel="Instructions (one per line)"
                toolsLabel="Tools"
                instructionsRows={5}
              />
              <Collapsible className="rounded-md border border-border/80">
                <CollapsibleTrigger className="flex w-full items-center justify-between px-3 py-2 text-left text-sm font-medium hover:bg-muted/50">
                  System prompt (read-only)
                  <ChevronDown className="size-4 shrink-0 opacity-50" />
                </CollapsibleTrigger>
                <CollapsibleContent>
                  <div className="max-h-48 overflow-auto border-t border-border/80 bg-muted/30 p-3">
                    {systemPromptLoading ? (
                      <p className="text-muted-foreground text-sm">
                        Loading…
                      </p>
                    ) : (
                      <pre className="whitespace-pre-wrap break-words font-mono text-xs text-foreground">
                        {systemPrompt ?? ""}
                      </pre>
                    )}
                  </div>
                </CollapsibleContent>
              </Collapsible>
              {updateAgent.error && (
                <p className="text-sm text-destructive" role="alert">
                  {(updateAgent.error as { message?: string })?.message ??
                    "Update failed"}
                </p>
              )}
              <div className="flex gap-2">
                <Button type="submit" disabled={updateAgent.isPending}>
                  {updateAgent.isPending ? "Saving…" : "Save"}
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setEditAgent(null)}
                >
                  Cancel
                </Button>
              </div>
            </form>
          )}
        </SheetContent>
      </Sheet>

      <AlertDialog
        open={deleteAgent != null}
        onOpenChange={(o) => !o && setDeleteAgent(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete agent?</AlertDialogTitle>
            <AlertDialogDescription>
              This will permanently delete &quot;
              {deleteAgent?.name ?? "this agent"}&quot; and its instructions.
              This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              onClick={() =>
                deleteAgent &&
                deleteAgentMutationState.mutate({
                  path: { agent_id: deleteAgent.agent_id },
                })
              }
              disabled={deleteAgentMutationState.isPending}
            >
              {deleteAgentMutationState.isPending ? "Deleting…" : "Delete"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
