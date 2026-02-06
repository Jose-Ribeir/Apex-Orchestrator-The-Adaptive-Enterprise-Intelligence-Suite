"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  listAgentsOptions,
  listAgentsQueryKey,
  updateAgentMutation,
  deleteAgentMutation,
  listToolsOptions,
} from "@ai-router/client/react-query";
import type { Agent, Tool } from "@ai-router/client";
import { Button } from "@ai-router/ui/button";
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
import { Pencil, Trash2, Bot } from "lucide-react";
import { useActiveAgent } from "@/providers/active-agent";
import { AgentFormFields } from "@/components/agent-form-fields";
import {
  defaultAgentFormValues,
  agentToFormValues,
  getAgentBodyFromValues,
} from "@/lib/agent-form";
import { agentModeLabel, formatDate } from "@/lib/format";

export default function SettingsAgentsPage() {
  const queryClient = useQueryClient();
  const { agentId: activeAgentId, setAgentId } = useActiveAgent();
  const [editAgent, setEditAgent] = useState<Agent | null>(null);
  const [deleteAgent, setDeleteAgent] = useState<Agent | null>(null);

  const { data: agentsResponse, isPending } = useQuery(listAgentsOptions({}));
  const agents: Agent[] =
    (agentsResponse as { data?: Agent[] } | undefined)?.data ?? [];

  const { data: toolsData } = useQuery({
    ...listToolsOptions({}),
    enabled: editAgent != null,
  });
  const toolsList: Tool[] =
    (toolsData as { data?: Tool[] } | undefined)?.data ?? [];

  const updateAgent = useMutation({
    ...updateAgentMutation(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: listAgentsQueryKey({}) });
      setEditAgent(null);
    },
  });

  const [editFormValues, setEditFormValues] = useState(defaultAgentFormValues);

  const openEditSheet = (agent: Agent) => {
    setEditAgent(agent);
    setEditFormValues(agentToFormValues(agent));
  };

  const deleteAgentMutationState = useMutation({
    ...deleteAgentMutation(),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: listAgentsQueryKey({}) });
      if (activeAgentId === variables.path.id) {
        setAgentId(null);
      }
      setDeleteAgent(null);
    },
  });

  const handleEditSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!editAgent?.id) return;
    const name = editFormValues.name.trim();
    if (!name) return;
    const body = getAgentBodyFromValues(editFormValues);
    updateAgent.mutate({
      path: { id: editAgent.id },
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
      ) : agents.length === 0 ? (
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
            {agents.map((agent) => (
              <TableRow key={agent.id}>
                <TableCell className="font-medium">
                  <span className="flex items-center gap-2">
                    <Bot className="size-4 text-muted-foreground" />
                    {agent.name ?? "—"}
                  </span>
                </TableCell>
                <TableCell>{agentModeLabel(agent.mode)}</TableCell>
                <TableCell>{formatDate(agent.updatedAt)}</TableCell>
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

      <Sheet open={editAgent != null} onOpenChange={(o) => !o && setEditAgent(null)}>
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
              This will permanently delete &quot;{deleteAgent?.name ?? "this agent"}&quot; and
              its instructions. This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              onClick={() =>
                deleteAgent &&
                deleteAgentMutationState.mutate({ path: { id: deleteAgent.id! } })
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
