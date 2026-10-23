export type VerificationMode = "off" | "lexical_grounding" | "semantic_entailment";
export type JobStatus = "queued" | "running" | "finished";
export type TerminalStatus = "answered" | "clarified" | "refused" | "error";

export interface Citation {
  article_id: string;
  law_name?: string | null;
  exact_quote?: string | null;
  title?: string | null;
  source_url?: string | null;
  source_pages?: number[] | null;
  source_sha256?: string | null;
  scope?: string | null;
  available: boolean;
}

export interface RunSnapshot {
  terminal_status: TerminalStatus;
  final_output: {
    action?: string;
    content?: string;
    question?: string;
    reason?: string;
    error_kind?: string;
    verified?: boolean | null;
    from_cache?: boolean;
    citations?: Citation[];
  };
  verification_mode?: VerificationMode | null;
  budgets: {
    tool_calls: { used: number; limit: number };
    repairs: { used: number; limit: number };
    steps: { used: number; limit: number };
  } | null;
  retrieved_article_ids?: string[];
  grounding: {
    label: string;
    grounded_ratio: number | null;
    sentences: Array<{ sentence: string; overlap_ratio: number; is_supported: boolean; best_article_id: string }>;
    unsupported_claims: string[];
    invalid_citations: string[];
  } | null;
  usage: {
    model_call_count: number | null;
    input_tokens: number | null;
    output_tokens: number | null;
    model_wall_ms: number | null;
  } | null;
  elapsed_ms: number | null;
}

export interface RunRecord {
  run_id: string;
  query: string;
  verification_mode: VerificationMode;
  job_status: JobStatus;
  terminal_status: TerminalStatus | null;
  created_at: number;
  updated_at: number;
  snapshot: RunSnapshot | null;
  pasted_document?: string | null;
}

export interface Capabilities {
  available: boolean;
  reason: string | null;
  model?: { provider: string; name: string };
  corpus?: { available: boolean; name: string; scope: string; retrieval: string };
  verification_modes: VerificationMode[];
  semantic_unavailable_reason: string | null;
  budgets?: { max_tool_calls: number; max_repairs: number; max_steps: number; wall_seconds: number };
  queue?: { waiting_limit: number; single_inference_worker: boolean };
  web_storage?: { retention_days: number; database_location: string };
}

export interface Article {
  article_id: string;
  title: string;
  content: string;
  law_name: string;
  scope?: string | null;
  source_url?: string | null;
  source_pages?: number[] | null;
  source_sha256?: string | null;
  extraction?: string | null;
}

export interface ActivityEvent {
  id: string;
  event: string;
  data: Record<string, unknown>;
  created_at: number;
}

export interface Proposal {
  proposal_id: string;
  recipient: string;
  content: string;
  payload_hash: string;
  status: "pending_confirmation" | "completed" | "expired";
  delivery: string;
  result?: { status?: string; delivered?: boolean; [key: string]: unknown } | null;
  event_id?: number;
  event_created_at?: number;
}
