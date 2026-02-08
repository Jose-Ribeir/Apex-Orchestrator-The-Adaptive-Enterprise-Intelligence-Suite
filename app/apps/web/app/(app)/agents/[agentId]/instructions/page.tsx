import {
  createAgentInstructionMutation,
  deleteAgentInstructionMutation,
  listAgentInstructionsOptions,
  listAgentInstructionsQueryKey,
  updateAgentInstructionMutation,
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
import { Field, FieldGroup, FieldLabel } from "@ai-router/ui/field";
import { Input } from "@ai-router/ui/input";
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
import { Textarea } from "@ai-router/ui/textarea";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Pencil, Plus, Trash2 } from "lucide-react";
import { useState } from "react";
import { useParams } from "react-router-dom";

type InstructionItem = {
  id: string;
  content?: string;
  order?: number;
  createdAt?: string;
  updatedAt?: string;
};

export default function AgentInstructionsPage() {
  const params = useParams();
  const agentId = params?.agentId as string;
  const queryClient = useQueryClient();
  const [createOpen, setCreateOpen] = useState(false);
  const [editing, setEditing] = useState<InstructionItem | null>(null);
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const [content, setContent] = useState("");
  const [order, setOrder] = useState(0);

  const { data: response, isPending } = useQuery({
    ...listAgentInstructionsOptions({ path: { agent_id: agentId } }),
    enabled: Boolean(agentId),
  });
  const instructions: InstructionItem[] =
    (response as { data?: InstructionItem[] } | undefined)?.data ?? [];

  const createInstruction = useMutation({
    ...createAgentInstructionMutation(),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: listAgentInstructionsQueryKey({
          path: { agent_id: agentId },
        }),
      });
      setCreateOpen(false);
      setContent("");
      setOrder(0);
    },
  });

  const updateInstruction = useMutation({
    ...updateAgentInstructionMutation(),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: listAgentInstructionsQueryKey({
          path: { agent_id: agentId },
        }),
      });
      setEditing(null);
      setContent("");
      setOrder(0);
    },
  });

  const deleteInstruction = useMutation({
    ...deleteAgentInstructionMutation(),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: listAgentInstructionsQueryKey({
          path: { agent_id: agentId },
        }),
      });
      setDeleteId(null);
    },
  });

  function openCreate() {
    setContent("");
    setOrder(instructions.length);
    setCreateOpen(true);
  }

  function openEdit(inst: InstructionItem) {
    setEditing(inst);
    setContent(inst.content ?? "");
    setOrder(inst.order ?? 0);
  }

  function handleCreateSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!content.trim()) return;
    createInstruction.mutate({
      path: { agent_id: agentId },
      body: { content: content.trim(), order },
    });
  }

  function handleUpdateSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!editing?.id || !content.trim()) return;
    updateInstruction.mutate({
      path: { agent_id: agentId, id: editing.id },
      body: { content: content.trim(), order },
    });
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-1">
        <h1 className="text-2xl font-bold">Instructions</h1>
        <p className="text-muted-foreground">
          Ordered instructions for this agent.
        </p>
      </div>

      <div className="flex items-center justify-between gap-4">
        <div className="flex-1" />
        <Button onClick={openCreate}>
          <Plus className="size-4" />
          Add instruction
        </Button>
      </div>

      {!agentId ? (
        <p className="text-muted-foreground text-sm">No agent selected.</p>
      ) : isPending ? (
        <p className="text-muted-foreground text-sm">Loading…</p>
      ) : instructions.length === 0 ? (
        <p className="text-muted-foreground text-sm">
          No instructions yet. Add one to get started.
        </p>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-16">Order</TableHead>
              <TableHead>Content</TableHead>
              <TableHead className="w-[120px]" />
            </TableRow>
          </TableHeader>
          <TableBody>
            {instructions
              .sort((a, b) => (a.order ?? 0) - (b.order ?? 0))
              .map((inst) => (
                <TableRow key={inst.id}>
                  <TableCell>{inst.order ?? 0}</TableCell>
                  <TableCell className="max-w-md truncate">
                    {inst.content ?? "—"}
                  </TableCell>
                  <TableCell>
                    <div className="flex gap-1">
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => openEdit(inst)}
                        aria-label="Edit"
                      >
                        <Pencil className="size-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="text-destructive hover:text-destructive"
                        onClick={() => setDeleteId(inst.id ?? null)}
                        aria-label="Delete"
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

      <Sheet open={createOpen} onOpenChange={setCreateOpen}>
        <SheetContent side="right" className="w-full max-w-md sm:max-w-md">
          <SheetHeader>
            <SheetTitle>Add instruction</SheetTitle>
          </SheetHeader>
          <form
            onSubmit={handleCreateSubmit}
            className="mt-6 flex flex-col gap-4"
          >
            <FieldGroup>
              <Field>
                <FieldLabel htmlFor="inst-content">Content</FieldLabel>
                <Textarea
                  id="inst-content"
                  value={content}
                  onChange={(e) => setContent(e.target.value)}
                  disabled={createInstruction.isPending}
                  rows={4}
                  className="resize-none"
                />
              </Field>
              <Field>
                <FieldLabel htmlFor="inst-order">Order</FieldLabel>
                <Input
                  id="inst-order"
                  type="number"
                  min={0}
                  value={order}
                  onChange={(e) => setOrder(parseInt(e.target.value, 10) || 0)}
                  disabled={createInstruction.isPending}
                />
              </Field>
            </FieldGroup>
            {createInstruction.error && (
              <p className="text-sm text-destructive" role="alert">
                {(createInstruction.error as { message?: string })?.message ??
                  "Failed to create"}
              </p>
            )}
            <div className="flex gap-2">
              <Button type="submit" disabled={createInstruction.isPending}>
                {createInstruction.isPending ? "Adding…" : "Add"}
              </Button>
              <Button
                type="button"
                variant="outline"
                onClick={() => setCreateOpen(false)}
              >
                Cancel
              </Button>
            </div>
          </form>
        </SheetContent>
      </Sheet>

      <Sheet
        open={editing != null}
        onOpenChange={(open) => !open && setEditing(null)}
      >
        <SheetContent side="right" className="w-full max-w-md sm:max-w-md">
          <SheetHeader>
            <SheetTitle>Edit instruction</SheetTitle>
          </SheetHeader>
          <form
            onSubmit={handleUpdateSubmit}
            className="mt-6 flex flex-col gap-4"
          >
            <FieldGroup>
              <Field>
                <FieldLabel htmlFor="edit-content">Content</FieldLabel>
                <Textarea
                  id="edit-content"
                  value={content}
                  onChange={(e) => setContent(e.target.value)}
                  disabled={updateInstruction.isPending}
                  rows={4}
                  className="resize-none"
                />
              </Field>
              <Field>
                <FieldLabel htmlFor="edit-order">Order</FieldLabel>
                <Input
                  id="edit-order"
                  type="number"
                  min={0}
                  value={order}
                  onChange={(e) => setOrder(parseInt(e.target.value, 10) || 0)}
                  disabled={updateInstruction.isPending}
                />
              </Field>
            </FieldGroup>
            {updateInstruction.error && (
              <p className="text-sm text-destructive" role="alert">
                {(updateInstruction.error as { message?: string })?.message ??
                  "Failed to update"}
              </p>
            )}
            <div className="flex gap-2">
              <Button type="submit" disabled={updateInstruction.isPending}>
                {updateInstruction.isPending ? "Saving…" : "Save"}
              </Button>
              <Button
                type="button"
                variant="outline"
                onClick={() => setEditing(null)}
              >
                Cancel
              </Button>
            </div>
          </form>
        </SheetContent>
      </Sheet>

      <AlertDialog
        open={deleteId != null}
        onOpenChange={(open) => !open && setDeleteId(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete instruction?</AlertDialogTitle>
            <AlertDialogDescription>
              This cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              onClick={() =>
                deleteId &&
                deleteInstruction.mutate({
                  path: { agent_id: agentId, id: deleteId },
                })
              }
              disabled={deleteInstruction.isPending}
            >
              {deleteInstruction.isPending ? "Deleting…" : "Delete"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
