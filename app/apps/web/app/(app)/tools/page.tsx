"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  listToolsOptions,
  listToolsQueryKey,
  createToolMutation,
  updateToolMutation,
  deleteToolMutation,
} from "@ai-router/client/react-query";
import type { Tool } from "@ai-router/client";
import { Button } from "@ai-router/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@ai-router/ui/table";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@ai-router/ui/sheet";
import { Field, FieldGroup, FieldLabel } from "@ai-router/ui/field";
import { Input } from "@ai-router/ui/input";
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
import { Pencil, Plus, Trash2 } from "lucide-react";

function formatDate(d: Date | null | undefined): string {
  if (!d) return "—";
  const date = typeof d === "string" ? new Date(d) : d;
  return date.toLocaleString();
}

export default function ToolsPage() {
  const queryClient = useQueryClient();
  const [createOpen, setCreateOpen] = useState(false);
  const [editing, setEditing] = useState<Tool | null>(null);
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const [name, setName] = useState("");

  const { data: response, isPending } = useQuery(listToolsOptions({}));
  const tools: Tool[] = (response as { data?: Tool[] } | undefined)?.data ?? [];

  const createTool = useMutation({
    ...createToolMutation(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: listToolsQueryKey({}) });
      setCreateOpen(false);
      setName("");
    },
  });

  const updateTool = useMutation({
    ...updateToolMutation(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: listToolsQueryKey({}) });
      setEditing(null);
      setName("");
    },
  });

  const deleteTool = useMutation({
    ...deleteToolMutation(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: listToolsQueryKey({}) });
      setDeleteId(null);
    },
  });

  function handleCreateSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    createTool.mutate({ body: { name: name.trim() } });
  }

  function handleUpdateSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!editing?.id || !name.trim()) return;
    updateTool.mutate({
      path: { id: editing.id },
      body: { name: name.trim() },
    });
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-1">
        <h1 className="text-2xl font-bold">Tools</h1>
        <p className="text-muted-foreground">
          Tool catalog. Assign tools to agents from the Agent section.
        </p>
      </div>

      <div className="flex items-center justify-between gap-4">
        <div className="flex-1" />
        <Button
          onClick={() => {
            setName("");
            setCreateOpen(true);
          }}
        >
          <Plus className="size-4" />
          Add tool
        </Button>
      </div>

      {isPending ? (
        <p className="text-muted-foreground text-sm">Loading…</p>
      ) : tools.length === 0 ? (
        <p className="text-muted-foreground text-sm">
          No tools in catalog yet. Create one to assign to agents.
        </p>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Created</TableHead>
              <TableHead className="w-[120px]" />
            </TableRow>
          </TableHeader>
          <TableBody>
            {tools.map((tool) => (
              <TableRow key={tool.id}>
                <TableCell className="font-medium">
                  {tool.name ?? tool.id ?? "—"}
                </TableCell>
                <TableCell>{formatDate(tool.createdAt)}</TableCell>
                <TableCell>
                  <div className="flex gap-1">
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => {
                        setEditing(tool);
                        setName(tool.name ?? "");
                      }}
                      aria-label="Edit"
                    >
                      <Pencil className="size-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="text-destructive hover:text-destructive"
                      onClick={() => setDeleteId(tool.id ?? null)}
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
            <SheetTitle>Add tool</SheetTitle>
          </SheetHeader>
          <form
            onSubmit={handleCreateSubmit}
            className="mt-6 flex flex-col gap-4"
          >
            <FieldGroup>
              <Field>
                <FieldLabel htmlFor="tool-name">Name</FieldLabel>
                <Input
                  id="tool-name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. Search"
                  disabled={createTool.isPending}
                />
              </Field>
            </FieldGroup>
            {createTool.error && (
              <p className="text-sm text-destructive" role="alert">
                {(createTool.error as { message?: string })?.message ??
                  "Failed to create"}
              </p>
            )}
            <div className="flex gap-2">
              <Button type="submit" disabled={createTool.isPending}>
                {createTool.isPending ? "Adding…" : "Add"}
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
            <SheetTitle>Edit tool</SheetTitle>
          </SheetHeader>
          <form
            onSubmit={handleUpdateSubmit}
            className="mt-6 flex flex-col gap-4"
          >
            <FieldGroup>
              <Field>
                <FieldLabel htmlFor="edit-tool-name">Name</FieldLabel>
                <Input
                  id="edit-tool-name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  disabled={updateTool.isPending}
                />
              </Field>
            </FieldGroup>
            {updateTool.error && (
              <p className="text-sm text-destructive" role="alert">
                {(updateTool.error as { message?: string })?.message ??
                  "Failed to update"}
              </p>
            )}
            <div className="flex gap-2">
              <Button type="submit" disabled={updateTool.isPending}>
                {updateTool.isPending ? "Saving…" : "Save"}
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
            <AlertDialogTitle>Delete tool?</AlertDialogTitle>
            <AlertDialogDescription>
              This will remove the tool from the catalog. Agents that had it
              assigned will no longer have it.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              onClick={() =>
                deleteId && deleteTool.mutate({ path: { id: deleteId } })
              }
              disabled={deleteTool.isPending}
            >
              {deleteTool.isPending ? "Deleting…" : "Delete"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
