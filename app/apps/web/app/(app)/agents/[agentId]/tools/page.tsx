import {
  addAgentToolMutation,
  listAgentToolsOptions,
  listAgentToolsQueryKey,
  listToolsOptions,
  removeAgentToolMutation,
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
import { Plus, Trash2 } from "lucide-react";
import { useState } from "react";
import { useParams } from "react-router-dom";

type ToolItem = { id?: string; name?: string; createdAt?: string };

export default function AgentToolsPage() {
  const params = useParams();
  const agentId = params?.agentId as string;
  const queryClient = useQueryClient();
  const [addOpen, setAddOpen] = useState(false);
  const [removeToolId, setRemoveToolId] = useState<string | null>(null);

  const { data: agentToolsResponse, isPending: loadingAgentTools } = useQuery({
    ...listAgentToolsOptions({ path: { agent_id: agentId } }),
    enabled: Boolean(agentId),
  });
  const agentTools: ToolItem[] =
    (agentToolsResponse as { data?: ToolItem[] } | undefined)?.data ?? [];

  const { data: catalogResponse } = useQuery({
    ...listToolsOptions({}),
    enabled: Boolean(agentId),
  });
  const catalogTools: ToolItem[] =
    (catalogResponse as { data?: ToolItem[] } | undefined)?.data ?? [];

  const assignedIds = new Set(agentTools.map((t) => t.id).filter(Boolean));
  const availableToAdd = catalogTools.filter(
    (t) => t.id && !assignedIds.has(t.id),
  );

  const addTool = useMutation({
    ...addAgentToolMutation(),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: listAgentToolsQueryKey({ path: { agent_id: agentId } }),
      });
      setAddOpen(false);
    },
  });

  const removeTool = useMutation({
    ...removeAgentToolMutation(),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: listAgentToolsQueryKey({ path: { agent_id: agentId } }),
      });
      setRemoveToolId(null);
    },
  });

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-1">
        <h1 className="text-2xl font-bold">Agent tools</h1>
        <p className="text-muted-foreground">
          Assign or remove tools from this agent.
        </p>
      </div>

      <div className="flex items-center justify-between gap-4">
        <div className="flex-1" />
        <Button
          onClick={() => setAddOpen(true)}
          disabled={availableToAdd.length === 0}
        >
          <Plus className="size-4" />
          Add tool
        </Button>
      </div>

      {!agentId ? (
        <p className="text-muted-foreground text-sm">No agent selected.</p>
      ) : loadingAgentTools ? (
        <p className="text-muted-foreground text-sm">Loading…</p>
      ) : agentTools.length === 0 ? (
        <p className="text-muted-foreground text-sm">
          No tools assigned. Add one from the catalog.
        </p>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead className="w-[80px]" />
            </TableRow>
          </TableHeader>
          <TableBody>
            {agentTools.map((tool) => (
              <TableRow key={tool.id}>
                <TableCell className="font-medium">
                  {tool.name ?? tool.id ?? "—"}
                </TableCell>
                <TableCell>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="text-destructive hover:text-destructive"
                    onClick={() => setRemoveToolId(tool.id ?? null)}
                    disabled={removeTool.isPending}
                    aria-label="Remove tool"
                  >
                    <Trash2 className="size-4" />
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}

      <Sheet open={addOpen} onOpenChange={setAddOpen}>
        <SheetContent side="right" className="w-full max-w-md sm:max-w-md">
          <SheetHeader>
            <SheetTitle>Add tool</SheetTitle>
          </SheetHeader>
          <div className="mt-6 flex flex-col gap-4">
            {availableToAdd.length === 0 ? (
              <p className="text-muted-foreground text-sm">
                All catalog tools are already assigned.
              </p>
            ) : (
              <ul className="flex flex-col gap-2">
                {availableToAdd.map((tool) => (
                  <li
                    key={tool.id}
                    className="flex items-center justify-between gap-2"
                  >
                    <span>{tool.name ?? tool.id}</span>
                    <Button
                      size="sm"
                      onClick={() =>
                        tool.id &&
                        addTool.mutate({
                          path: { agent_id: agentId },
                          body: { name: tool.name ?? "" },
                        })
                      }
                      disabled={addTool.isPending}
                    >
                      Add
                    </Button>
                  </li>
                ))}
              </ul>
            )}
            {addTool.error && (
              <p className="text-sm text-destructive" role="alert">
                {(addTool.error as { message?: string })?.message ??
                  "Failed to add tool"}
              </p>
            )}
            <Button variant="outline" onClick={() => setAddOpen(false)}>
              Close
            </Button>
          </div>
        </SheetContent>
      </Sheet>

      <AlertDialog
        open={removeToolId != null}
        onOpenChange={(open) => !open && setRemoveToolId(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Remove tool?</AlertDialogTitle>
            <AlertDialogDescription>
              This will unassign the tool from this agent. The tool stays in the
              catalog.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              onClick={() =>
                removeToolId &&
                removeTool.mutate({
                  path: { agent_id: agentId, tool_id: removeToolId },
                })
              }
              disabled={removeTool.isPending}
            >
              {removeTool.isPending ? "Removing…" : "Remove"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
