/* LuatCheck D2 — recorded-run inspector.
   Every field below is read from data/runs.json, exported from the app's SQLite store. */

const RUN_META = {
  "7a75d738-cc03-4722-839a-f3e15158b20a": { label: "Verified answer", domain: "HCMUT" },
  "5d5461fe-f386-4909-8571-4d4415962a57": { label: "Second corpus", domain: "Labour" },
  "1f837ce6-5f7c-495d-b5eb-353ba5348913": { label: "Repaired, then verified", domain: "HCMUT" },
  "410e06cb-1012-42e5-b186-01979d118215": { label: "Refused after repairs", domain: "HCMUT" },
  "e18d850a-da08-4096-a488-c2b3435aa247": { label: "Injection blocked", domain: "Guardrail" },
};

const RETRIEVAL_LABEL = {
  hybrid_wrrf: "Weighted RRF",
  bm25_tfidf: "BM25 + TF-IDF",
  fts5: "SQLite FTS5",
  vector: "Vector 768-d",
  rrf: "RRF 50/50",
};

const listEl = document.getElementById("run-list");
const detailEl = document.getElementById("run-detail");

let runs = [];
let active = 0;

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (ch) => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch]
  ));
}

function inline(text) {
  return escapeHtml(text).replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
}

function renderRichText(text) {
  const blocks = String(text || "").trim().split(/\n{2,}/).filter(Boolean);
  return blocks.map((block) => {
    const lines = block.split("\n");
    if (lines.every((line) => line.trim().startsWith("- "))) {
      return `<ul>${lines.map((line) => `<li>${inline(line.trim().slice(2))}</li>`).join("")}</ul>`;
    }
    return `<p>${inline(block).replace(/\n/g, "<br>")}</p>`;
  }).join("");
}

function fmtMs(ms) {
  if (ms === null || ms === undefined || Number.isNaN(ms)) return "—";
  if (ms < 1000) return `${Math.round(ms)} ms`;
  return `${(ms / 1000).toFixed(1)} s`;
}

function fmtK(n) {
  if (n === null || n === undefined) return "—";
  if (n >= 1000) return `${(n / 1000).toFixed(1)}k`;
  return String(n);
}

function fmtDate(iso) {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  const pad = (v) => String(v).padStart(2, "0");
  return `${d.getUTCFullYear()}-${pad(d.getUTCMonth() + 1)}-${pad(d.getUTCDate())} ` +
    `${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())} UTC`;
}

function fmtPages(pages) {
  if (!Array.isArray(pages) || !pages.length) return "";
  if (pages.length === 1) return `p. ${pages[0]}`;
  const min = Math.min(...pages);
  const max = Math.max(...pages);
  return min === max ? `p. ${min}` : `pp. ${min}–${max}`;
}

function statusOf(run) {
  if (run.terminal_status === "answered") {
    return run.answer.verified
      ? { cls: "answered", label: "ANSWERED · VERIFIED", short: "ANSWERED" }
      : { cls: "answered", label: "ANSWERED", short: "ANSWERED" };
  }
  if (run.refusal_kind === "guardrail") {
    return { cls: "guardrail", label: "BLOCKED · GUARDRAIL", short: "GUARDRAIL" };
  }
  if (run.refusal_kind === "verification_failed") {
    return { cls: "refused", label: "REFUSED · VERIFICATION", short: "REFUSED" };
  }
  return { cls: "refused", label: "REFUSED", short: "REFUSED" };
}

function renderList() {
  listEl.innerHTML = runs.map((run, index) => {
    const status = statusOf(run);
    const meta = RUN_META[run.id] || { label: "Recorded run", domain: run.profile?.id || "Run" };
    const label = run.id in RUN_META
      ? meta.label
      : (run.terminal_status === "answered" ? "Verified answer" : "Refused");
    return `
      <button class="run-item${index === active ? " is-active" : ""}" role="tab"
              id="run-tab-${index}" aria-selected="${index === active}"
              aria-controls="run-detail" tabindex="${index === active ? 0 : -1}"
              data-index="${index}">
        <span class="run-status ${status.cls}"><i aria-hidden="true"></i>${status.short}</span>
        <span class="run-label">${escapeHtml(label)}</span>
        <span class="run-q" lang="vi">${escapeHtml(run.query)}</span>
        <span class="run-meta"><span>${escapeHtml(meta.domain)}</span><span>${fmtMs(run.elapsed_ms)}</span></span>
      </button>`;
  }).join("");

  listEl.querySelectorAll(".run-item").forEach((button) => {
    button.addEventListener("click", () => selectRun(Number(button.dataset.index)));
    button.addEventListener("keydown", onTabKey);
  });
}

function onTabKey(event) {
  const keys = ["ArrowDown", "ArrowUp", "ArrowLeft", "ArrowRight", "Home", "End"];
  if (!keys.includes(event.key)) return;
  event.preventDefault();
  let next = active;
  if (event.key === "ArrowDown" || event.key === "ArrowRight") next = (active + 1) % runs.length;
  if (event.key === "ArrowUp" || event.key === "ArrowLeft") next = (active - 1 + runs.length) % runs.length;
  if (event.key === "Home") next = 0;
  if (event.key === "End") next = runs.length - 1;
  selectRun(next, true);
}

function selectRun(index, focus = false) {
  if (!runs.length) return;
  active = index;
  updateTabs();
  renderDetail();
  if (focus) {
    const tab = document.getElementById(`run-tab-${index}`);
    if (tab) tab.focus();
  }
}

function updateTabs() {
  listEl.querySelectorAll(".run-item").forEach((button, index) => {
    const isActive = index === active;
    button.classList.toggle("is-active", isActive);
    button.setAttribute("aria-selected", String(isActive));
    button.tabIndex = isActive ? 0 : -1;
  });
}

function renderTimeline(events) {
  return `<ol class="timeline">${events.map((event) => {
    const time = fmtMs(event.t);
    if (event.kind === "start") {
      return `
        <li class="tl-item start">
          <span class="tl-time">${time}</span>
          <span class="tl-marker"><span></span></span>
          <div>
            <p class="tl-title">Run started</p>
            <p class="tl-detail">Job accepted by the single inference worker.</p>
          </div>
        </li>`;
    }
    if (event.kind === "call") {
      const title = event.tool === "read_document" ? "Read section" : "Search";
      const detail = event.tool === "read_document"
        ? `<p class="tl-detail mono">${escapeHtml(event.detail)}</p>`
        : `<p class="tl-detail" lang="vi">“${escapeHtml(event.detail)}”</p>`;
      const chips = [
        event.wall_ms != null ? `model ${fmtMs(event.wall_ms)}` : "",
        event.input_tokens != null ? `${fmtK(event.input_tokens)} → ${fmtK(event.output_tokens)} tok` : "",
      ].filter(Boolean).map((chip) => `<span class="tl-chip">${chip}</span>`).join("");
      return `
        <li class="tl-item call">
          <span class="tl-time">${time}</span>
          <span class="tl-marker"><span></span></span>
          <div>
            <p class="tl-title">Model call → ${escapeHtml(title)} ${chips}</p>
            ${detail}
          </div>
        </li>`;
    }
    if (event.kind === "result") {
      const isRead = event.tool === "read_document";
      const title = isRead
        ? "Section loaded"
        : `${event.count ?? event.ids.length} sections retrieved`;
      const ids = event.ids.length
        ? `<div class="tl-ids">${event.ids.map((id) => `<span>${escapeHtml(id)}</span>`).join("")}</div>`
        : "";
      return `
        <li class="tl-item result">
          <span class="tl-time">${time}</span>
          <span class="tl-marker"><span></span></span>
          <div>
            <p class="tl-title">${escapeHtml(title)}</p>
            ${ids}
          </div>
        </li>`;
    }
    if (event.kind === "verify") {
      const passed = Boolean(event.passed);
      const chips = [
        event.action ? `action: ${event.action}` : "",
        event.wall_ms != null ? `${fmtMs(event.wall_ms)} model` : "",
        event.input_tokens != null ? `${fmtK(event.input_tokens)} → ${fmtK(event.output_tokens)} tok` : "",
      ].filter(Boolean).map((chip) => `<span class="tl-chip">${chip}</span>`).join("");
      return `
        <li class="tl-item verify ${passed ? "pass" : "fail"}">
          <span class="tl-time">${time}</span>
          <span class="tl-marker"><span></span></span>
          <div>
            <p class="tl-title">${passed ? "L1 verifier passed" : "L1 verifier rejected the draft"} ${chips}</p>
            <p class="tl-detail">${passed
              ? "All hard checks passed; the answer was released."
              : "Draft returned to the controller with the closest source passage."}</p>
          </div>
        </li>`;
    }
    if (event.kind === "repair") {
      return `
        <li class="tl-item repair">
          <span class="tl-time">${time}</span>
          <span class="tl-marker"><span></span></span>
          <div>
            <p class="tl-title">Repair attempt ${escapeHtml(event.attempt)} <span class="tl-chip">verifier feedback</span></p>
            <details>
              <summary>Read verifier feedback</summary>
              <pre class="tl-feedback">${escapeHtml(event.feedback)}</pre>
            </details>
          </div>
        </li>`;
    }
    if (event.kind === "finish") {
      return `
        <li class="tl-item finish">
          <span class="tl-time">${time}</span>
          <span class="tl-marker"><span></span></span>
          <div>
            <p class="tl-title">Run finished · ${escapeHtml(event.status)}</p>
            <p class="tl-detail">Trace and final output persisted to SQLite.</p>
          </div>
        </li>`;
    }
    return "";
  }).join("")}</ol>`;
}

function renderCitations(run) {
  const citations = run.citations || [];
  if (!citations.length) {
    return `<div class="no-citations">No citations returned. ${
      run.terminal_status === "refused"
        ? "The run ended without an answer, so there is nothing to cite."
        : ""
    }</div>`;
  }
  return citations.map((citation) => {
    const pages = fmtPages(citation.source_pages);
    const quote = citation.exact_quote
      ? `<blockquote lang="vi">“${escapeHtml(citation.exact_quote)}”</blockquote>`
      : `<p class="noquote">Section-level citation — no verbatim quote attached.</p>`;
    const link = citation.source_url
      ? `<a href="${escapeHtml(citation.source_url)}" target="_blank" rel="noopener">Official PDF ↗</a>`
      : "";
    return `
      <article class="citation">
        <div class="citation-head"><span>${escapeHtml(citation.article_id)}</span><span>${escapeHtml(pages)}</span></div>
        ${quote}
        <p class="law">${escapeHtml(citation.law_name || "")}</p>
        ${link}
      </article>`;
  }).join("");
}

function meter(label, used, limit) {
  const safeLimit = limit || 0;
  const pct = safeLimit ? Math.min(100, (used / safeLimit) * 100) : 0;
  const cls = used >= safeLimit ? "full" : "";
  return `
    <div class="meter">
      <div class="meter-label"><span>${escapeHtml(label)}</span><span><b>${used} / ${safeLimit}</b></span></div>
      <div class="bar"><i class="${cls}" style="width:${pct}%"></i></div>
    </div>`;
}

function renderOutcome(run) {
  const isRefusal = run.terminal_status === "refused";
  if (!isRefusal) {
    return `
      <article class="outcome answered">
        <div class="outcome-label"><span>Final output</span>${run.answer.verified ? '<span class="verified-tag">L1 VERIFIED</span>' : ""}</div>
        <div class="answer-text" lang="vi">${renderRichText(run.answer.content)}</div>
      </article>`;
  }

  const cls = run.refusal_kind === "guardrail" ? "guardrail" : "refused";
  let lead = "Refusal";
  if (run.refusal_kind === "guardrail") lead = "Blocked before any model call";
  else if (run.refusal_kind === "verification_failed") {
    const attempts = run.budgets?.repairs?.used ?? 0;
    lead = `Refused after ${attempts} failed repair${attempts === 1 ? "" : "s"}`;
  }
  return `
    <article class="outcome ${cls}">
      <div class="outcome-label"><span>${isRefusal ? "Refusal" : "Final output"}</span></div>
      <p class="refusal-reason"><span class="lead">${escapeHtml(lead)}</span>${escapeHtml(run.answer.reason || "No reason recorded.")}</p>
    </article>`;
}

function renderDetail() {
  const run = runs[active];
  if (!run) return;
  const status = statusOf(run);
  const meta = RUN_META[run.id] || { domain: run.profile?.id || "Run" };
  const usage = run.usage || {};
  const budgets = run.budgets || {};
  const steps = budgets.steps || { used: 0, limit: 0 };
  const tools = budgets.tool_calls || { used: 0, limit: 0 };
  const repairs = budgets.repairs || { used: 0, limit: 0 };
  const tokens = (usage.input_tokens || 0) + (usage.output_tokens || 0);

  const chips = [
    `${fmtMs(run.elapsed_ms)} total`,
    `${steps.used} / ${steps.limit} steps`,
    `${tools.used} / ${tools.limit} tool calls`,
    `${repairs.used} / ${repairs.limit} repairs`,
    `${usage.model_call_count ?? 0} model calls`,
    tokens ? `${fmtK(tokens)} tokens` : "",
    RETRIEVAL_LABEL[run.retrieval_mode] || run.retrieval_mode || "",
    run.verification_mode === "lexical_grounding" ? "L1 verifier" : (run.verification_mode || ""),
  ].filter(Boolean).map((chip) => `<span class="chip">${escapeHtml(chip)}</span>`).join("");

  const guardrailNote = run.refusal_kind === "guardrail"
    ? `<p class="tl-detail">Input policy rejected the request before retrieval (0 tool calls, 0 model calls, ${fmtK(0)} tokens).</p>`
    : "";

  detailEl.innerHTML = `
    <div class="detail-head">
      <div class="detail-head-left">
        <span class="status-pill ${status.cls}">${status.label}</span>
        <span class="pill ghost">${escapeHtml(run.profile?.id || "")}</span>
        <span class="pill ghost">${escapeHtml(meta.domain)}</span>
      </div>
      <span class="detail-date mono">${fmtDate(run.date)}</span>
    </div>
    <h3 class="detail-query" lang="vi">${escapeHtml(run.query)}</h3>
    <div class="chips">${chips}</div>
    <div class="detail-body">
      <section class="trace-col" aria-label="Run trace">
        <h4 class="col-title">Trace</h4>
        ${renderTimeline(run.timeline || [])}
        ${guardrailNote}
      </section>
      <div class="outcome-col">
        ${renderOutcome(run)}
        <section class="budgets" aria-label="Budgets">
          <h4 class="col-title">Budgets</h4>
          ${meter("Tool calls", tools.used, tools.limit)}
          ${meter("Repairs", repairs.used, repairs.limit)}
          ${meter("Steps", steps.used, steps.limit)}
        </section>
        <section class="citations" aria-label="Citations">
          <h4 class="col-title">Citations${run.citations.length ? ` · ${run.citations.length}` : ""}</h4>
          ${renderCitations(run)}
        </section>
      </div>
    </div>`;
}

async function init() {
  try {
    const response = await fetch("data/runs.json", { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    runs = data.runs || [];
    if (!runs.length) throw new Error("No runs in data/runs.json");
    renderList();
    renderDetail();
  } catch (error) {
    listEl.innerHTML = `<p class="loading">Trace data could not be loaded (${escapeHtml(error.message)}).</p>`;
    detailEl.innerHTML = `<div class="detail-placeholder"><p class="mono">Data unavailable</p><p>The page needs <code>data/runs.json</code> next to <code>index.html</code>.</p></div>`;
  }
}

init();
