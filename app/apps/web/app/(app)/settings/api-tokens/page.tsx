"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  listApiTokensOptions,
  listApiTokensQueryKey,
  createApiTokenMutation,
  revokeApiTokenMutation,
} from "@ai-router/client/react-query";
import type {
  ApiTokenListItem,
  CreateApiTokenResponse2,
} from "@ai-router/client";
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
import { Copy, Plus, Trash2 } from "lucide-react";

function formatDate(d: Date | null | undefined): string {
  if (!d) return "—";
  const date = typeof d === "string" ? new Date(d) : d;
  return date.toLocaleString();
}

export default function ApiTokensPage() {
  const queryClient = useQueryClient();
  const [createOpen, setCreateOpen] = useState(false);
  const [createdToken, setCreatedToken] =
    useState<CreateApiTokenResponse2 | null>(null);
  const [revokeId, setRevokeId] = useState<string | null>(null);
  const [createName, setCreateName] = useState("");
  const [createExpiresInDays, setCreateExpiresInDays] = useState("");

  const { data: tokensResponse, isPending } = useQuery(
    listApiTokensOptions({}),
  );
  const tokens: ApiTokenListItem[] =
    (tokensResponse as { data?: ApiTokenListItem[] } | undefined)?.data ?? [];

  const createToken = useMutation({
    ...createApiTokenMutation(),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: listApiTokensQueryKey({}) });
      setCreatedToken(data as CreateApiTokenResponse2);
      setCreateName("");
      setCreateExpiresInDays("");
    },
  });

  const revokeToken = useMutation({
    ...revokeApiTokenMutation(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: listApiTokensQueryKey({}) });
      setRevokeId(null);
    },
  });

  function handleCreateSubmit(e: React.FormEvent) {
    e.preventDefault();
    const body: { name?: string; expiresInDays?: number } = {};
    if (createName.trim()) body.name = createName.trim();
    const days = createExpiresInDays.trim()
      ? parseInt(createExpiresInDays, 10)
      : undefined;
    if (days != null && !Number.isNaN(days)) body.expiresInDays = days;
    createToken.mutate({ body });
  }

  function copyToken() {
    if (createdToken?.token) {
      void navigator.clipboard.writeText(createdToken.token);
    }
  }

  function closeCreateSheet() {
    setCreateOpen(false);
    setCreatedToken(null);
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-1">
        <h1 className="text-2xl font-bold">API tokens</h1>
        <p className="text-muted-foreground">
          Create and manage API tokens for Bearer authentication.
        </p>
      </div>

      <div className="flex items-center justify-between gap-4">
        <div className="flex-1" />
        <Button onClick={() => setCreateOpen(true)}>
          <Plus className="size-4" />
          Create token
        </Button>
      </div>

      {isPending ? (
        <p className="text-muted-foreground text-sm">Loading tokens…</p>
      ) : tokens.length === 0 ? (
        <p className="text-muted-foreground text-sm">
          No API tokens yet. Create one to use Bearer auth.
        </p>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Created</TableHead>
              <TableHead>Last used</TableHead>
              <TableHead>Expires</TableHead>
              <TableHead className="w-[80px]" />
            </TableRow>
          </TableHeader>
          <TableBody>
            {tokens.map((token) => (
              <TableRow key={token.id}>
                <TableCell className="font-medium">
                  {token.name ?? "—"}
                </TableCell>
                <TableCell>{formatDate(token.createdAt)}</TableCell>
                <TableCell>{formatDate(token.lastUsedAt)}</TableCell>
                <TableCell>{formatDate(token.expiresAt)}</TableCell>
                <TableCell>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="text-destructive hover:text-destructive"
                    onClick={() => setRevokeId(token.id ?? null)}
                    disabled={revokeToken.isPending}
                    aria-label="Revoke token"
                  >
                    <Trash2 className="size-4" />
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}

      <Sheet
        open={createOpen}
        onOpenChange={(open) => !open && closeCreateSheet()}
      >
        <SheetContent side="right" className="w-full max-w-md sm:max-w-md">
          <SheetHeader>
            <SheetTitle>
              {createdToken ? "Token created" : "Create API token"}
            </SheetTitle>
          </SheetHeader>
          <div className="mt-6">
            {createdToken ? (
              <div className="flex flex-col gap-4">
                <p className="text-muted-foreground text-sm">
                  Copy the token now. It won&apos;t be shown again.
                </p>
                <div className="flex gap-2">
                  <Input
                    readOnly
                    value={createdToken.token}
                    className="font-mono text-sm"
                  />
                  <Button
                    variant="outline"
                    size="icon"
                    onClick={copyToken}
                    aria-label="Copy token"
                  >
                    <Copy className="size-4" />
                  </Button>
                </div>
                <Button onClick={closeCreateSheet}>Done</Button>
              </div>
            ) : (
              <form
                onSubmit={handleCreateSubmit}
                className="flex flex-col gap-4"
              >
                <FieldGroup>
                  <Field>
                    <FieldLabel htmlFor="token-name">
                      Name (optional)
                    </FieldLabel>
                    <Input
                      id="token-name"
                      placeholder="e.g. CI, Dashboard"
                      value={createName}
                      onChange={(e) => setCreateName(e.target.value)}
                      disabled={createToken.isPending}
                    />
                  </Field>
                  <Field>
                    <FieldLabel htmlFor="token-expires">
                      Expires in days (optional)
                    </FieldLabel>
                    <Input
                      id="token-expires"
                      type="number"
                      min="1"
                      placeholder="e.g. 90"
                      value={createExpiresInDays}
                      onChange={(e) => setCreateExpiresInDays(e.target.value)}
                      disabled={createToken.isPending}
                    />
                  </Field>
                </FieldGroup>
                {createToken.error && (
                  <p className="text-sm text-destructive" role="alert">
                    {(createToken.error as { message?: string })?.message ??
                      "Failed to create token"}
                  </p>
                )}
                <div className="flex gap-2">
                  <Button type="submit" disabled={createToken.isPending}>
                    {createToken.isPending ? "Creating…" : "Create"}
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    onClick={closeCreateSheet}
                  >
                    Cancel
                  </Button>
                </div>
              </form>
            )}
          </div>
        </SheetContent>
      </Sheet>

      <AlertDialog
        open={revokeId != null}
        onOpenChange={(open) => !open && setRevokeId(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Revoke token?</AlertDialogTitle>
            <AlertDialogDescription>
              This will invalidate the token immediately. Any clients using it
              will get 401.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              onClick={() =>
                revokeId && revokeToken.mutate({ path: { id: revokeId } })
              }
              disabled={revokeToken.isPending}
            >
              {revokeToken.isPending ? "Revoking…" : "Revoke"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
