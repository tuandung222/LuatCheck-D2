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
    pre_model_policy_refusal?: boolean | null;
    citations?: Citation[];
  };
  refusal_kind?: "guardrail" | "verification_failed" | "model" | null;
  profile?: { id: string; display_name?: string | null } | null;
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
  profile_id?: string | null;
  created_at: number;
  updated_at: number;
  snapshot: RunSnapshot | null;
  pasted_document?: string | null;
}

export interface Suggestion { tag?: string; text: string }

export interface ProfileInfo {
  id: string;
  available: boolean;
  error?: string | null;
  short_name?: string | null;
  scope_note?: string | null;
  suggestions: Suggestion[];
  config_file?: string | null;
  display_name?: string;
  source_name?: string;
  search_tool?: string;
  read_tool?: string;
  id_example?: string;
  corpus?: { records: number | null; documents: number | null };
  retrieval?: {
    mode: string;
    first_stage: string;
    reranker: { enabled: boolean; backend: string | null; model: string | null; top_k_in: number | null; top_k_out: number | null };
  };
  verifier_mode?: string;
}

export interface Capabilities {
  available: boolean;
  reason: string | null;
  model?: { provider: string; name: string; endpoint?: string } | null;
  profiles?: ProfileInfo[];
  default_profile?: string | null;
  default_verification_mode?: VerificationMode;
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

export interface ModelCallInfo {
  wall_ms?: number | null;
  input_tokens?: number | null;
  output_tokens?: number | null;
  outcome?: string | null;
  error_kind?: string | null;
  action?: string | null;
}

export interface ResultRef { id: string; title: string }

export interface RerankInfo {
  backend?: string;
  model?: string;
  top_k_in?: number;
  top_k_out?: number;
  n_candidates?: number;
  n_scored?: number;
  n_truncated?: number;
  first_stage_ms?: number;
  wall_ms?: number;
  ms_per_pair?: number;
  first_stage_ids?: string[];
  reranked_ids?: string[];
}

export interface Health {
  api: string;
  configuration: string;
  corpus: string;
  model: { status: string; reachable: boolean | null; configured_model_present: boolean | null };
  reranker?: { enabled: boolean | null; backend?: string; model?: string | null; reachable: boolean | null };
  active_run: boolean;
  queued_runs: number;
}
