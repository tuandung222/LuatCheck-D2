import type {
  ActivityEvent,
  Article,
  Capabilities,
  CorpusChunksResponse,
  CorpusOverview,
  Health,
  Proposal,
  RetrievalMode,
  RunRecord,
  VerificationMode,
} from "./types";

let csrfToken = "";

export class ApiError extends Error {
  constructor(message: string, readonly status: number) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body) headers.set("Content-Type", "application/json");
  if (init.method && init.method !== "GET") headers.set("X-CSRF-Token", csrfToken);
  const response = await fetch(path, { ...init, headers, credentials: "include" });
  if (!response.ok) {
    let message = `HTTP ${response.status}`;
    try {
      const body = await response.json();
      if (typeof body.detail === "string") message = body.detail;
    } catch {
      // Keep the HTTP status when the server did not return JSON.
    }
    throw new ApiError(message, response.status);
  }
  return response.json() as Promise<T>;
}

export async function initialize(): Promise<void> {
  const response = await request<{ csrf_token: string }>("/api/v1/session");
  csrfToken = response.csrf_token;
}

export const getCapabilities = () => request<Capabilities>("/api/v1/capabilities");
export const getHealth = () => request<Health>("/api/v1/health");

export const listRuns = () => request<{ items: RunRecord[]; total: number }>("/api/v1/runs?limit=30");
export const getRun = (runId: string) => request<RunRecord>(`/api/v1/runs/${encodeURIComponent(runId)}`);
export const getArticle = (runId: string, articleId: string) =>
  request<Article>(`/api/v1/runs/${encodeURIComponent(runId)}/articles/${encodeURIComponent(articleId)}`);

export async function createRun(
  query: string,
  pastedDocument: string,
  verificationMode: VerificationMode,
  idempotencyKey: string,
  profile?: string,
  retrievalMode?: RetrievalMode,
) {
  return request<{ run_id: string; job_status: string; replayed: boolean }>("/api/v1/runs", {
    method: "POST",
    headers: { "Idempotency-Key": idempotencyKey },
    body: JSON.stringify({
      query,
      pasted_document: pastedDocument || null,
      verification_mode: verificationMode,
      retrieval_mode: retrievalMode ?? null,
      profile: profile ?? null,
    }),
  });
}

export const createProposal = (runId: string, recipient: string, content: string) =>
  request<Proposal>(`/api/v1/runs/${encodeURIComponent(runId)}/summary-proposals`, {
    method: "POST",
    body: JSON.stringify({ recipient, content }),
  });

export const confirmProposal = (proposal: Proposal) =>
  request<{ proposal_id: string; status: string; replayed: boolean; event_id?: number; event_created_at?: number; display_message?: string; result?: { status?: string; delivered?: boolean } }>(
    `/api/v1/summary-proposals/${encodeURIComponent(proposal.proposal_id)}/confirm`,
    { method: "POST", body: JSON.stringify({ payload_hash: proposal.payload_hash }) },
  );

export function subscribeToRun(runId: string, onEvent: (event: ActivityEvent) => void, onError: () => void) {
  const source = new EventSource(`/api/v1/runs/${encodeURIComponent(runId)}/events`, { withCredentials: true });
  const names = [
    "run_queued", "run_started", "model_call_started", "tool_completed", "verification_completed",
    "repair_started", "run_finished", "run_persisted", "run_failed", "run_interrupted",
    "summary_proposal_created", "summary_proposal_completed",
  ];
  for (const name of names) {
    source.addEventListener(name, (message) => {
      const data = message as MessageEvent<string>;
      let parsed: Record<string, unknown> = {};
      try {
        parsed = JSON.parse(data.data) as Record<string, unknown>;
      } catch {
        parsed = {};
      }
      onEvent({
        id: data.lastEventId,
        event: name,
        data: parsed,
        created_at: typeof parsed.created_at === "number" ? parsed.created_at : Date.now() / 1000,
      });
    });
  }
  source.onerror = onError;
  return source;
}

export const getCorpusOverview = (corpus: string = "labour") =>
  request<CorpusOverview>(`/api/corpus/overview?corpus=${encodeURIComponent(corpus)}`);

export const getCorpusChunks = (params: {
  corpus?: string;
  doc_code?: string;
  q?: string;
  chapter?: string;
  limit?: number;
  offset?: number;
}) => {
  const qp = new URLSearchParams();
  if (params.corpus) qp.set("corpus", params.corpus);
  if (params.doc_code) qp.set("doc_code", params.doc_code);
  if (params.q) qp.set("q", params.q);
  if (params.chapter) qp.set("chapter", params.chapter);
  if (params.limit != null) qp.set("limit", String(params.limit));
  if (params.offset != null) qp.set("offset", String(params.offset));
  return request<CorpusChunksResponse>(`/api/corpus/chunks?${qp.toString()}`);
};
