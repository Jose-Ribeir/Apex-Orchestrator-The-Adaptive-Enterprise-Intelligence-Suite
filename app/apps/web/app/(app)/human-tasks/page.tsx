"use client";

import { formatDateTime } from "@/lib/format";
import type { HumanTaskResponse } from "@ai-router/client";
import {
  listHumanTasksOptions,
  resolveHumanTaskMutation,
} from "@ai-router/client/react-query";
import { Badge } from "@ai-router/ui/badge";
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
import { Check, Pencil } from "lucide-react";
import { useState } from "react";

export default function HumanTasksPage() {
  const queryClient = useQueryClient();
  const [detailTask, setDetailTask] = useState<HumanTaskResponse | null>(null);
  const [statusFilter, setStatusFilter] = useState<boolean | undefined>(
    undefined,
  );

  const { data: response, isPending } = useQuery({
    ...listHumanTasksOptions({
      query: {
        page: 1,
        limit: 50,
        ...(statusFilter !== undefined ? { pending: statusFilter } : {}),
      },
    }),
  });
  const tasks: HumanTaskResponse[] = response?.data ?? [];

  const resolveTask = useMutation({
    ...resolveHumanTaskMutation(),
    onSuccess: () => {
      queryClient.invalidateQueries({
        predicate: (query) =>
          (query.queryKey[0] as { _id?: string })?._id === "listHumanTasks",
      });
      setDetailTask(null);
    },
  });

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-1">
        <h1 className="text-2xl font-bold">Human tasks</h1>
        <p className="text-muted-foreground">
          Human-in-the-loop tasks linked to model queries.
        </p>
      </div>

      <div className="flex items-center gap-2">
        <Button
          variant={statusFilter === undefined ? "default" : "outline"}
          size="sm"
          onClick={() => setStatusFilter(undefined)}
        >
          All
        </Button>
        <Button
          variant={statusFilter === true ? "default" : "outline"}
          size="sm"
          onClick={() => setStatusFilter(true)}
        >
          Pending
        </Button>
        <Button
          variant={statusFilter === false ? "default" : "outline"}
          size="sm"
          onClick={() => setStatusFilter(false)}
        >
          Resolved
        </Button>
      </div>

      {isPending ? (
        <p className="text-muted-foreground text-sm">Loading…</p>
      ) : tasks.length === 0 ? (
        <p className="text-muted-foreground text-sm">No human tasks.</p>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Status</TableHead>
              <TableHead>Reason</TableHead>
              <TableHead>Model message</TableHead>
              <TableHead>Created</TableHead>
              <TableHead className="w-[100px]" />
            </TableRow>
          </TableHeader>
          <TableBody>
            {tasks.map((task) => (
              <TableRow key={task.id}>
                <TableCell>
                  <Badge
                    variant={
                      task.status === "PENDING" ? "default" : "secondary"
                    }
                  >
                    {task.status ?? "—"}
                  </Badge>
                </TableCell>
                <TableCell className="max-w-xs truncate">
                  {task.reason ?? "—"}
                </TableCell>
                <TableCell className="max-w-xs truncate">
                  {task.modelMessage ?? "—"}
                </TableCell>
                <TableCell>{formatDateTime(task.createdAt)}</TableCell>
                <TableCell>
                  <div className="flex gap-1">
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => setDetailTask(task)}
                      aria-label="View"
                    >
                      <Pencil className="size-4" />
                    </Button>
                    {task.status === "PENDING" && (
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() =>
                          resolveTask.mutate({
                            path: { task_id: task.id },
                          })
                        }
                        disabled={resolveTask.isPending}
                        aria-label="Resolve"
                      >
                        <Check className="size-4" />
                      </Button>
                    )}
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}

      <Sheet
        open={detailTask != null}
        onOpenChange={(open) => !open && setDetailTask(null)}
      >
        <SheetContent side="right" className="w-full max-w-lg sm:max-w-lg">
          <SheetHeader>
            <SheetTitle>Human task</SheetTitle>
          </SheetHeader>
          {detailTask && (
            <div className="mt-6 flex flex-col gap-4">
              <div>
                <span className="text-muted-foreground text-sm">Status</span>
                <p className="font-medium">{detailTask.status ?? "—"}</p>
              </div>
              <div>
                <span className="text-muted-foreground text-sm">Reason</span>
                <p className="whitespace-pre-wrap">
                  {detailTask.reason ?? "—"}
                </p>
              </div>
              <div>
                <span className="text-muted-foreground text-sm">
                  Model message
                </span>
                <p className="whitespace-pre-wrap">
                  {detailTask.modelMessage ?? "—"}
                </p>
              </div>
              <div>
                <span className="text-muted-foreground text-sm">
                  Retrieved data
                </span>
                <p className="whitespace-pre-wrap text-sm">
                  {detailTask.retrievedData ?? "—"}
                </p>
              </div>
              <div>
                <span className="text-muted-foreground text-sm">Created</span>
                <p>{formatDateTime(detailTask.createdAt)}</p>
              </div>
              {detailTask.status === "PENDING" && (
                <Button
                  onClick={() =>
                    resolveTask.mutate({
                      path: { task_id: detailTask.id },
                    })
                  }
                  disabled={resolveTask.isPending}
                >
                  {resolveTask.isPending ? "Resolving…" : "Mark resolved"}
                </Button>
              )}
              <Button variant="outline" onClick={() => setDetailTask(null)}>
                Close
              </Button>
            </div>
          )}
        </SheetContent>
      </Sheet>
    </div>
  );
}
