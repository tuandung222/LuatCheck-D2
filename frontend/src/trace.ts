import type { ActivityEvent, ModelCallInfo, RerankInfo, ResultRef, TerminalStatus } from "./types";

/** One row of the readable run timeline. Everything here is read from recorded run events; nothing is estimated. */
export type StepKind = "guardrail" | "search" | "read" | "verify" | "repair" | "clarify" | "refuse" | "error" | "running";

export interface TraceStep {
  key: string;
  kind: StepKind;
  startMs: number;
  durationMs: number | null;
  model?: ModelCallInfo | null;
  tool?: string;
  query?: string;
  requestedId?: string;
  results?: ResultRef[];
  rerank?: RerankInfo | null;
  verifyMode?: string;
  passed?: boolean;
  attempt?: number;
  feedback?: string;
  errorKind?: string;
  failedTool?: { tool?: string; query?: string; error_kind?: string };
  modelStep?: number;
  terminal?: TerminalStatus;
}

export interface Trace {
  steps: TraceStep[];
  queueMs: number | null;
  finished: boolean;
  totalMs: number | null;
  /** created_at (epoch seconds) of run_started, used for the live timer. */
  startedAt: number | null;
}

function num(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function relMs(event: ActivityEvent, startedAt: number | null): number {
  const t = num(event.data.t_ms);
  if (t !== null) return t;
  return startedAt === null ? 0 : Math.max(0, (event.created_at - startedAt) * 1000);
}

export function buildTrace(events: ActivityEvent[]): Trace {
  const steps: TraceStep[] = [];
  let startedAt: number | null = null;
  let queuedAt: number | null = null;
  let queueMs: number | null = null;
  let cur: { startMs: number; step: number } | null = null;
  let finished = false;
  let totalMs: number | null = null;

  for (const event of events) {
    const d = event.data;
    switch (event.event) {
      case "run_queued":
        queuedAt = event.created_at;
        break;
      case "run_started":
        startedAt = event.created_at;
        if (queuedAt !== null) queueMs = Math.max(0, (event.created_at - queuedAt) * 1000);
        break;
      case "model_call_started":
        cur = { startMs: relMs(event, startedAt), step: Number(d.step ?? steps.length + 1) };
        break;
      case "tool_completed": {
        const end = relMs(event, startedAt);
        const isSearch = d.query !== undefined;
        steps.push({
          key: `s${event.id}`, kind: isSearch ? "search" : "read", startMs: cur?.startMs ?? end,
          durationMs: cur ? Math.max(0, end - cur.startMs) : null, model: (d.model as ModelCallInfo) ?? null,
          tool: typeof d.tool === "string" ? d.tool : undefined, query: typeof d.query === "string" ? d.query : undefined,
          requestedId: typeof d.requested_id === "string" ? d.requested_id : undefined,
          results: Array.isArray(d.results) ? (d.results as ResultRef[]) : (Array.isArray(d.article_ids) ? (d.article_ids as string[]).map((id) => ({ id, title: "" })) : []),
          rerank: (d.rerank as RerankInfo) ?? null, modelStep: cur?.step,
        });
        cur = null;
        break;
      }
      case "verification_completed": {
        const end = relMs(event, startedAt);
        steps.push({
          key: `s${event.id}`, kind: "verify", startMs: cur?.startMs ?? end, durationMs: cur ? Math.max(0, end - cur.startMs) : null,
          model: (d.model as ModelCallInfo) ?? null, verifyMode: String(d.mode ?? ""), passed: Boolean(d.passed), modelStep: cur?.step,
        });
        cur = null;
        break;
      }
      case "repair_started": {
        steps.push({
          key: `s${event.id}`, kind: "repair", startMs: relMs(event, startedAt), durationMs: 0,
          attempt: Number(d.attempt ?? 0), feedback: typeof d.feedback === "string" ? d.feedback : undefined,
        });
        break;
      }
      case "run_finished": {
        finished = true;
        const end = relMs(event, startedAt);
        totalMs = end;
        const terminal = String(d.terminal_status ?? "") as TerminalStatus;
        const failedTool = (d.failed_tool as TraceStep["failedTool"]) ?? undefined;
        if (cur) {
          const kind: StepKind = terminal === "clarified" ? "clarify" : terminal === "refused" ? "refuse" : terminal === "error" ? "error" : "running";
          steps.push({
            key: `s${event.id}`, kind, startMs: cur.startMs, durationMs: Math.max(0, end - cur.startMs), model: (d.model as ModelCallInfo) ?? null,
            errorKind: typeof d.error_kind === "string" ? d.error_kind : undefined, failedTool, modelStep: cur.step, terminal,
          });
          cur = null;
        } else if (steps.length === 0 && terminal === "refused") {
          steps.push({ key: `s${event.id}`, kind: "guardrail", startMs: 0, durationMs: end, terminal });
        } else if (terminal === "refused" || terminal === "error") {
          steps.push({
            key: `s${event.id}`, kind: terminal === "error" ? "error" : "refuse", startMs: end, durationMs: 0,
            errorKind: typeof d.error_kind === "string" ? d.error_kind : undefined, failedTool, terminal,
          });
        }
        break;
      }
      case "run_failed":
        finished = true;
        steps.push({ key: `s${event.id}`, kind: "error", startMs: 0, durationMs: null, errorKind: String(d.error_kind ?? "execution_error"), terminal: "error" });
        break;
      case "run_interrupted":
        finished = true;
        steps.push({ key: `s${event.id}`, kind: "error", startMs: 0, durationMs: null, errorKind: "api_restart", terminal: "error" });
        break;
      default:
        break;
    }
  }
  if (!finished && cur) {
    steps.push({ key: "running", kind: "running", startMs: cur.startMs, durationMs: null, modelStep: cur.step });
  }
  return { steps, queueMs, finished, totalMs, startedAt };
}
