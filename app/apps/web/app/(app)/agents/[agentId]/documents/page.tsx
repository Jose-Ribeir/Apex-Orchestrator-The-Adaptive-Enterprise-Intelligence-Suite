"use client";

import {
  ingestAgentDocumentMutation,
} from "@ai-router/client/react-query";
import { Button } from "@ai-router/ui/button";
import { useMutation } from "@tanstack/react-query";
import { FileStack, Upload, X } from "lucide-react";
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
  const hasExt = ALLOWED_EXTENSIONS.some((ext) => name.endsWith(ext));
  return hasExt && file.size <= MAX_FILE_SIZE_BYTES;
}

export default function AgentDocumentsPage() {
  const params = useParams();
  const agentId = params?.agentId as string;
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [result, setResult] = useState<{
    docs_added: number;
    total_docs: number;
  } | null>(null);
  const [dragOver, setDragOver] = useState(false);

  const ingestMutation = useMutation({
    ...ingestAgentDocumentMutation(),
    onError: (err) => setError(err instanceof Error ? err.message : "Upload failed"),
  });

  const [error, setError] = useState<string | null>(null);

  const uploadFiles = useCallback(async () => {
    if (!agentId || selectedFiles.length === 0) return;
    setError(null);
    setResult(null);
    let totalAdded = 0;
    let lastTotal = 0;
    for (const file of selectedFiles) {
      if (!isAllowedFile(file)) {
        setError(
          `File "${file.name}" is not allowed. Use PDF, TXT, or DOCX; max ${MAX_FILE_SIZE_MB} MB per file.`,
        );
        return;
      }
      const contentBase64 = await fileToBase64(file);
      try {
        const data = await ingestMutation.mutateAsync({
          path: { agentId },
          body: { filename: file.name, contentBase64 },
        });
        totalAdded += data?.docs_added ?? 0;
        lastTotal = data?.total_docs ?? 0;
      } catch {
        return;
      }
    }
    setResult({ docs_added: totalAdded, total_docs: lastTotal });
    setSelectedFiles([]);
  }, [agentId, selectedFiles, ingestMutation]);

  const onFileSelect = useCallback((files: FileList | null) => {
    if (!files) return;
    const list = Array.from(files).filter((f) => isAllowedFile(f));
    setSelectedFiles((prev) => [...prev, ...list]);
    setError(null);
  }, []);

  const removeFile = useCallback((index: number) => {
    setSelectedFiles((prev) => prev.filter((_, i) => i !== index));
    setError(null);
  }, []);

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-1">
        <h1 className="text-2xl font-bold">Documents</h1>
        <p className="text-muted-foreground">
          Upload PDF, TXT, or DOCX files. They are converted to text and indexed
          for RAG (embeddings are created automatically).
        </p>
      </div>

      <div
        className={`rounded-xl border-2 border-dashed p-8 text-center transition-colors ${dragOver
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
          id="documents-file-input"
          onChange={(e) => onFileSelect(e.target.files)}
        />
        <label
          htmlFor="documents-file-input"
          className="flex cursor-pointer flex-col items-center gap-2"
        >
          <FileStack className="size-10 text-muted-foreground" />
          <span className="text-muted-foreground">
            Drag files here or click to browse
          </span>
          <span className="text-muted-foreground text-sm">
            PDF, TXT, DOCX · max {MAX_FILE_SIZE_MB} MB per file
          </span>
        </label>
      </div>

      {selectedFiles.length > 0 && (
        <div className="flex flex-col gap-2">
          <p className="text-muted-foreground text-sm">
            {selectedFiles.length} file(s) selected
          </p>
          <ul className="flex flex-col gap-1 rounded-lg border bg-muted/30 p-2">
            {selectedFiles.map((file, i) => (
              <li
                key={`${file.name}-${i}`}
                className="flex items-center justify-between gap-2 rounded px-2 py-1.5 text-sm"
              >
                <span className="truncate">{file.name}</span>
                <span className="text-muted-foreground shrink-0">
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
            >
              {ingestMutation.isPending ? (
                "Uploading…"
              ) : (
                <>
                  <Upload className="size-4" />
                  Upload and index
                </>
              )}
            </Button>
          </div>
        </div>
      )}

      {error && (
        <p className="rounded-lg border border-destructive/50 bg-destructive/10 px-3 py-2 text-sm text-destructive" role="alert">
          {error}
        </p>
      )}

      {result && (
        <p className="rounded-lg border border-green-500/30 bg-green-500/10 px-3 py-2 text-sm text-green-700 dark:text-green-400" role="status">
          Indexed {result.docs_added} chunk(s). Total documents in RAG:{" "}
          {result.total_docs}.
        </p>
      )}

      {!agentId && (
        <p className="text-muted-foreground text-sm">No agent selected.</p>
      )}
    </div>
  );
}
