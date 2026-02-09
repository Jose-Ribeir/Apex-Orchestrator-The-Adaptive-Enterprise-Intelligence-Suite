"use client";

import {
  addAgentDocumentMutation,
  deleteAgentDocumentMutation,
  ingestAgentDocumentMutation,
  ingestAgentDocumentUrlMutation,
  listAgentDocumentsOptions,
  listAgentDocumentsQueryKey,
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
import {
  Download,
  FileText,
  Link2,
  Plus,
  Trash2,
  Upload,
  X,
} from "lucide-react";
import { useCallback, useState } from "react";
import { useParams } from "react-router-dom";

const ALLOWED_EXTENSIONS = [".pdf", ".txt", ".docx"];
const MAX_FILE_SIZE_MB = 20;
const MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024;

function fileToBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const dataUrl = reader.result as string;
      const base64 = dataUrl.slice(dataUrl.indexOf(",") + 1);
      resolve(base64);
    };
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(file);
  });
}

function isAllowedFile(file: File): boolean {
  const name = file.name.toLowerCase();
  return (
    ALLOWED_EXTENSIONS.some((ext) => name.endsWith(ext)) &&
    file.size <= MAX_FILE_SIZE_BYTES
  );
}

type DocItem = {
  id: string;
  name?: string;
  sourceFilename?: string | null;
  downloadUrl?: string | null;
  sourceType?: string | null;
  sourceUrl?: string | null;
  createdAt?: string;
};

export default function AgentDocumentsPage() {
  const params = useParams();
  const agentId = params?.agentId as string;
  const queryClient = useQueryClient();
  const [addOpen, setAddOpen] = useState(false);
  const [deleteDocId, setDeleteDocId] = useState<string | null>(null);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [dragOver, setDragOver] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [addMode, setAddMode] = useState<"files" | "text" | "url">("files");
  const [pastedText, setPastedText] = useState("");
  const [pastedTitle, setPastedTitle] = useState("");
  const [urlInput, setUrlInput] = useState("");

  const { data: listResponse, isPending: loadingList } = useQuery({
    ...listAgentDocumentsOptions({
      path: { agent_id: agentId },
      query: { page: 1, limit: 50 },
    }),
    enabled: Boolean(agentId),
  });
  const docs: DocItem[] = Array.isArray(
    (listResponse as { data?: DocItem[] })?.data,
  )
    ? (listResponse as { data: DocItem[] }).data
    : [];
  const meta = (listResponse as { meta?: { total?: number } })?.meta;
  const totalDocs = meta?.total ?? 0;

  const ingestMutation = useMutation({
    ...ingestAgentDocumentMutation(),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: listAgentDocumentsQueryKey({ path: { agent_id: agentId } }),
      });
    },
  });

  const addTextMutation = useMutation({
    ...addAgentDocumentMutation(),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: listAgentDocumentsQueryKey({ path: { agent_id: agentId } }),
      });
      setPastedText("");
      setPastedTitle("");
      setAddOpen(false);
    },
  });

  const ingestUrlMutation = useMutation({
    ...ingestAgentDocumentUrlMutation(),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: listAgentDocumentsQueryKey({ path: { agent_id: agentId } }),
      });
      setUrlInput("");
      setAddOpen(false);
    },
  });

  const deleteMutation = useMutation({
    ...deleteAgentDocumentMutation(),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: listAgentDocumentsQueryKey({ path: { agent_id: agentId } }),
      });
      setDeleteDocId(null);
    },
  });

  const onFileSelect = useCallback((files: FileList | null) => {
    if (!files) return;
    const list = Array.from(files).filter((f) => isAllowedFile(f));
    setSelectedFiles((prev) => [...prev, ...list]);
    setUploadError(null);
  }, []);

  const removeFile = useCallback((index: number) => {
    setSelectedFiles((prev) => prev.filter((_, i) => i !== index));
    setUploadError(null);
  }, []);

  const uploadFiles = useCallback(async () => {
    if (!agentId || selectedFiles.length === 0) return;
    setUploadError(null);
    for (const file of selectedFiles) {
      if (!isAllowedFile(file)) {
        setUploadError(
          `"${file.name}" not allowed. Use PDF, TXT, or DOCX; max ${MAX_FILE_SIZE_MB} MB.`,
        );
        return;
      }
      try {
        const contentBase64 = await fileToBase64(file);
        await ingestMutation.mutateAsync({
          path: { agent_id: agentId },
          body: { filename: file.name, contentBase64 },
        });
      } catch (e) {
        setUploadError(
          e instanceof Error ? e.message : `Failed to upload ${file.name}`,
        );
        return;
      }
    }
    setSelectedFiles([]);
    setAddOpen(false);
  }, [agentId, selectedFiles, ingestMutation]);

  const closeAddSheet = useCallback(() => {
    setAddOpen(false);
    setSelectedFiles([]);
    setUploadError(null);
    setPastedText("");
    setPastedTitle("");
    setUrlInput("");
  }, []);

  const addPastedText = useCallback(async () => {
    if (!agentId || !pastedText.trim()) return;
    setUploadError(null);
    try {
      await addTextMutation.mutateAsync({
        path: { agent_id: agentId },
        body: {
          content: pastedText.trim(),
          metadata: pastedTitle.trim()
            ? { title: pastedTitle.trim() }
            : undefined,
        },
      });
    } catch (e) {
      setUploadError(e instanceof Error ? e.message : "Failed to add text");
    }
  }, [agentId, pastedText, pastedTitle, addTextMutation]);

  const addUrl = useCallback(async () => {
    if (!agentId || !urlInput.trim()) return;
    setUploadError(null);
    try {
      await ingestUrlMutation.mutateAsync({
        path: { agent_id: agentId },
        body: { url: urlInput.trim() },
      });
    } catch (e) {
      setUploadError(e instanceof Error ? e.message : "Failed to add URL");
    }
  }, [agentId, urlInput, ingestUrlMutation]);

  const typeLabel = (d: DocItem) => {
    const t = (d.sourceType || "").toLowerCase();
    if (t === "url") return "URL";
    if (t === "text") return "Text";
    return "File";
  };

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-1">
        <h1 className="text-2xl font-bold">Knowledge Base</h1>
        <p className="text-muted-foreground">
          Add text, files (PDF, TXT, DOCX), or URLs. Content is indexed for RAG.
          Use the button below to add to the knowledge base.
        </p>
      </div>

      <div className="flex items-center justify-between gap-4">
        <div className="flex-1" />
        <Button onClick={() => setAddOpen(true)} disabled={!agentId}>
          <Plus className="size-4" />
          Add to knowledge base
        </Button>
      </div>

      {!agentId ? (
        <p className="text-muted-foreground text-sm">No agent selected.</p>
      ) : loadingList ? (
        <p className="text-muted-foreground text-sm">Loading…</p>
      ) : docs.length === 0 ? (
        <p className="text-muted-foreground text-sm">
          No knowledge base items yet. Add text, files, or URLs to index for
          RAG.
        </p>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead className="w-[80px]">Type</TableHead>
              <TableHead className="hidden sm:table-cell">Source</TableHead>
              <TableHead className="text-right">Created</TableHead>
              <TableHead className="w-[100px]">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {docs.map((d) => (
              <TableRow key={d.id}>
                <TableCell className="font-medium">
                  {d.name ?? d.sourceFilename ?? d.id ?? "—"}
                </TableCell>
                <TableCell className="text-muted-foreground text-sm">
                  {typeLabel(d)}
                </TableCell>
                <TableCell className="hidden text-muted-foreground sm:table-cell">
                  {d.sourceUrl ? (
                    <a
                      href={d.sourceUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-primary hover:underline truncate block max-w-[200px]"
                    >
                      {d.sourceUrl}
                    </a>
                  ) : (
                    (d.sourceFilename ?? "—")
                  )}
                </TableCell>
                <TableCell className="text-right text-muted-foreground text-sm">
                  {d.createdAt
                    ? new Date(d.createdAt).toLocaleDateString(undefined, {
                        dateStyle: "short",
                      })
                    : "—"}
                </TableCell>
                <TableCell>
                  <div className="flex items-center justify-end gap-1">
                    {d.downloadUrl && (
                      <Button
                        variant="ghost"
                        size="icon"
                        asChild
                        aria-label="Download or view file"
                      >
                        <a
                          href={d.downloadUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          <Download className="size-4" />
                        </a>
                      </Button>
                    )}
                    {d.sourceUrl && !d.downloadUrl && (
                      <Button
                        variant="ghost"
                        size="icon"
                        asChild
                        aria-label="Open URL"
                      >
                        <a
                          href={d.sourceUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          <Link2 className="size-4" />
                        </a>
                      </Button>
                    )}
                    <Button
                      variant="ghost"
                      size="icon"
                      className="text-destructive hover:text-destructive"
                      onClick={() => setDeleteDocId(d.id)}
                      disabled={deleteMutation.isPending}
                      aria-label="Delete knowledge base item"
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

      {totalDocs > 0 && (
        <p className="text-muted-foreground text-sm">
          {totalDocs} item{totalDocs !== 1 ? "s" : ""} in knowledge base.
        </p>
      )}

      {/* Add to knowledge base: right sidebar with files / text / URL */}
      <Sheet open={addOpen} onOpenChange={(open) => !open && closeAddSheet()}>
        <SheetContent side="right" className="w-full max-w-md sm:max-w-md">
          <SheetHeader>
            <SheetTitle>Add to knowledge base</SheetTitle>
          </SheetHeader>
          <div className="mt-6 flex flex-1 flex-col gap-4">
            <div className="flex gap-1 rounded-lg border bg-muted/30 p-1">
              <Button
                type="button"
                variant={addMode === "files" ? "secondary" : "ghost"}
                size="sm"
                className="flex-1"
                onClick={() => setAddMode("files")}
              >
                <Upload className="size-4 mr-1" />
                Files
              </Button>
              <Button
                type="button"
                variant={addMode === "text" ? "secondary" : "ghost"}
                size="sm"
                className="flex-1"
                onClick={() => setAddMode("text")}
              >
                <FileText className="size-4 mr-1" />
                Text
              </Button>
              <Button
                type="button"
                variant={addMode === "url" ? "secondary" : "ghost"}
                size="sm"
                className="flex-1"
                onClick={() => setAddMode("url")}
              >
                <Link2 className="size-4 mr-1" />
                URL
              </Button>
            </div>

            {addMode === "files" && (
              <>
                <div
                  className={`flex min-h-[180px] flex-col items-center justify-center rounded-xl border-2 border-dashed p-6 text-center transition-colors ${
                    dragOver
                      ? "border-primary bg-primary/5"
                      : "border-muted-foreground/25 hover:border-muted-foreground/50"
                  }`}
                  onDragOver={(e) => {
                    e.preventDefault();
                    setDragOver(true);
                  }}
                  onDragLeave={() => setDragOver(false)}
                  onDrop={(e) => {
                    e.preventDefault();
                    setDragOver(false);
                    onFileSelect(e.dataTransfer.files);
                  }}
                >
                  <input
                    type="file"
                    accept=".pdf,.txt,.docx"
                    multiple
                    className="hidden"
                    id="add-docs-file-input"
                    onChange={(e) => onFileSelect(e.target.files)}
                  />
                  <label
                    htmlFor="add-docs-file-input"
                    className="flex cursor-pointer flex-col items-center gap-2"
                  >
                    <Upload className="size-10 text-muted-foreground" />
                    <span className="text-muted-foreground text-sm font-medium">
                      Drag files here or click to browse
                    </span>
                    <span className="text-muted-foreground text-xs">
                      PDF, TXT, DOCX · max {MAX_FILE_SIZE_MB} MB per file
                    </span>
                  </label>
                </div>
                {selectedFiles.length > 0 && (
                  <div className="flex flex-col gap-2">
                    <p className="text-muted-foreground text-sm font-medium">
                      {selectedFiles.length} file(s) selected
                    </p>
                    <ul className="flex max-h-[180px] flex-col gap-1 overflow-y-auto rounded-lg border bg-muted/30 p-2">
                      {selectedFiles.map((file, i) => (
                        <li
                          key={`${file.name}-${i}`}
                          className="flex items-center justify-between gap-2 rounded px-2 py-1.5 text-sm"
                        >
                          <span className="truncate">{file.name}</span>
                          <span className="text-muted-foreground shrink-0 text-xs">
                            {(file.size / 1024).toFixed(1)} KB
                          </span>
                          <Button
                            type="button"
                            variant="ghost"
                            size="icon"
                            className="size-7 shrink-0"
                            onClick={() => removeFile(i)}
                            aria-label="Remove file"
                          >
                            <X className="size-4" />
                          </Button>
                        </li>
                      ))}
                    </ul>
                    <div className="flex gap-2">
                      <Button
                        onClick={uploadFiles}
                        disabled={ingestMutation.isPending}
                        className="flex-1"
                      >
                        {ingestMutation.isPending
                          ? "Uploading…"
                          : `Upload ${selectedFiles.length} file(s)`}
                      </Button>
                      <Button variant="outline" onClick={closeAddSheet}>
                        Cancel
                      </Button>
                    </div>
                  </div>
                )}
              </>
            )}

            {addMode === "text" && (
              <div className="flex flex-col gap-3">
                <div>
                  <label className="text-muted-foreground text-sm font-medium">
                    Title (optional)
                  </label>
                  <input
                    type="text"
                    className="mt-1 w-full rounded-md border bg-background px-3 py-2 text-sm"
                    placeholder="e.g. My notes"
                    value={pastedTitle}
                    onChange={(e) => setPastedTitle(e.target.value)}
                  />
                </div>
                <div>
                  <label className="text-muted-foreground text-sm font-medium">
                    Text content
                  </label>
                  <textarea
                    className="mt-1 min-h-[160px] w-full rounded-md border bg-background px-3 py-2 text-sm"
                    placeholder="Paste or type text to index…"
                    value={pastedText}
                    onChange={(e) => setPastedText(e.target.value)}
                  />
                </div>
                <div className="flex gap-2">
                  <Button
                    onClick={addPastedText}
                    disabled={!pastedText.trim() || addTextMutation.isPending}
                    className="flex-1"
                  >
                    {addTextMutation.isPending ? "Adding…" : "Add text"}
                  </Button>
                  <Button variant="outline" onClick={closeAddSheet}>
                    Cancel
                  </Button>
                </div>
              </div>
            )}

            {addMode === "url" && (
              <div className="flex flex-col gap-3">
                <p className="text-muted-foreground text-sm">
                  Enter a URL. The page will be fetched and main content
                  extracted and indexed (navigation and ads are ignored).
                </p>
                <input
                  type="url"
                  className="w-full rounded-md border bg-background px-3 py-2 text-sm"
                  placeholder="https://example.com/article"
                  value={urlInput}
                  onChange={(e) => setUrlInput(e.target.value)}
                />
                <div className="flex gap-2">
                  <Button
                    onClick={addUrl}
                    disabled={!urlInput.trim() || ingestUrlMutation.isPending}
                    className="flex-1"
                  >
                    {ingestUrlMutation.isPending ? "Fetching…" : "Add URL"}
                  </Button>
                  <Button variant="outline" onClick={closeAddSheet}>
                    Cancel
                  </Button>
                </div>
              </div>
            )}

            {uploadError && (
              <p
                className="rounded-lg border border-destructive/50 bg-destructive/10 px-3 py-2 text-sm text-destructive"
                role="alert"
              >
                {uploadError}
              </p>
            )}
          </div>
        </SheetContent>
      </Sheet>

      <AlertDialog
        open={deleteDocId != null}
        onOpenChange={(open) => !open && setDeleteDocId(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Remove from knowledge base?</AlertDialogTitle>
            <AlertDialogDescription>
              This will remove this item from the agent&apos;s RAG index and
              delete its record. This cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              onClick={() =>
                deleteDocId &&
                agentId &&
                deleteMutation.mutate({
                  path: { agent_id: agentId, document_id: deleteDocId },
                })
              }
              disabled={deleteMutation.isPending}
            >
              {deleteMutation.isPending ? "Removing…" : "Remove"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
