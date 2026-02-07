import type { Request, Response } from "express";
import { ingestDocument } from "../../../integrations/geminimesh";
import { ValidationError } from "../../../lib/errors";
import { paramUuid } from "../../../lib/params";
import { agentService } from "../services/agents.service";

const MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024; // 20 MB
const ALLOWED_EXTENSIONS = [".pdf", ".txt", ".docx"];

/**
 * POST /api/agents/:agentId/documents/ingest
 * Body: { filename: string, contentBase64: string }
 * Verifies agent access, decodes file, sends to Python API for text extraction and RAG indexing.
 */
async function ingestDocumentHandler(
  req: Request,
  res: Response,
): Promise<void> {
  const agentId = paramUuid(req.params.agentId);
  const userId = req.user!.id;

  await agentService.getById(agentId, userId);

  const body = req.body as { filename?: string; contentBase64?: string };
  const filename =
    typeof body.filename === "string" ? body.filename.trim() : "";
  const contentBase64 = body.contentBase64;

  if (!filename) {
    throw new ValidationError("filename is required");
  }
  if (typeof contentBase64 !== "string" || !contentBase64) {
    throw new ValidationError("contentBase64 is required");
  }

  const ext = filename.toLowerCase().includes(".")
    ? filename.toLowerCase().slice(filename.toLowerCase().lastIndexOf("."))
    : "";
  if (!ALLOWED_EXTENSIONS.includes(ext)) {
    throw new ValidationError(
      `Unsupported file type. Allowed: ${ALLOWED_EXTENSIONS.join(", ")}`,
    );
  }

  let buffer: Buffer;
  try {
    buffer = Buffer.from(contentBase64, "base64");
  } catch {
    throw new ValidationError("contentBase64 is not valid base64");
  }

  if (buffer.length > MAX_FILE_SIZE_BYTES) {
    throw new ValidationError(
      `File too large (max ${MAX_FILE_SIZE_BYTES / 1024 / 1024} MB)`,
    );
  }

  const blob = new Blob([new Uint8Array(buffer)]);
  const result = await ingestDocument(agentId, blob, filename);
  res.json(result);
}

export const documentsController = {
  ingest: ingestDocumentHandler,
};
