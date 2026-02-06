/**
 * Types for Gemini Agent Factory (GeminiMesh) API v6.4
 * @see https://geminimesh.mainet.uk/docs
 */

export type AgentConfigMode = "PERFORMANCE" | "EFFICIENCY" | "BALANCED";

/** Request body for update_agent_prompt_geminimesh and optimize_prompt */
export interface AgentConfig {
  agent_id: string;
  name: string;
  mode?: AgentConfigMode;
  instructions: string[];
  tools?: string[];
}

/** Request body for generate_stream */
export interface ChatRequest {
  agent_id: string;
  message: string;
  system_prompt: string;
}

/** Request body for update_agent_index */
export interface UpdateAgentRequest {
  agent_id: string;
  action: string;
  doc_id?: string | null;
  content?: string | null;
  metadata?: Record<string, unknown> | null;
}

/** Multipart form fields for upload_and_index */
export interface UploadAndIndexForm {
  agent_id: string;
  file: Blob | File;
}
