import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ArrowDown, ArrowUpRight, BookOpen, Check, ChevronDown, ChevronRight, CircleAlert, CircleCheck, Clock3, FileText, History, Info,
  LoaderCircle, Menu, Moon, Plus, Scale, Send, Settings2, ShieldCheck, Sparkles, Sun, X, CircleHelp, ShieldAlert, Ban,
} from "lucide-react";
import {
  ApiError, confirmProposal, createProposal, createRun, getArticle, getCapabilities, getHealth,
  getRun, initialize, listRuns, subscribeToRun,
} from "./api";
import { SectionErrorBoundary } from "./ErrorBoundary";
import { formatClock, formatDuration } from "./format";
import { LexicalPanel, Measurements, OutcomeCard, SourceItem, WorkingCard, type ArticleState } from "./Results";
import { ProfileSwitch, SystemStrip } from "./SystemBar";
import { Timeline } from "./Timeline";
import { buildTrace } from "./trace";
import type {
  ActivityEvent, Capabilities, Health, ProfileInfo, Proposal, RunRecord, TerminalStatus, VerificationMode,
} from "./types";

function statusText(run: RunRecord) {
  if (run.job_status === "queued") return "Đang xếp hàng";
  if (run.job_status === "running") return "Đang xử lý";
  const kind = run.snapshot?.refusal_kind;
  switch (run.terminal_status) {
    case "answered": return "Có câu trả lời";
    case "clarified": return "Hỏi lại";
    case "refused": return kind === "guardrail" ? "Chặn bởi guardrail" : "Từ chối";
    case "error": return "Lỗi thực thi";
    default: return "Chưa chạy";
  }
}

function stateClass(run: RunRecord) {
  if (run.job_status !== "finished") return "active";
  if (run.terminal_status === "refused" && run.snapshot?.refusal_kind === "guardrail") return "guardrail";
  return run.terminal_status ?? "error";
}

function StateIcon({ run, size = 15 }: { run: RunRecord; size?: number }) {
  const s = stateClass(run);
  if (s === "active") return <LoaderCircle size={size} className="spinning" />;
  if (s === "answered") return <CircleCheck size={size} />;
  if (s === "clarified") return <CircleHelp size={size} />;
  if (s === "guardrail") return <ShieldAlert size={size} />;
  if (s === "refused") return <Ban size={size} />;
  if (s === "error") return <CircleAlert size={size} />;
  return <Clock3 size={size} />;
}

function modeName(mode: VerificationMode | null | undefined) {
  if (!mode) return "—";
  if (mode === "off") return "OFF (không kiểm tra)";
  if (mode === "semantic_entailment") return "L1 + L2 (semantic)";
  return "L1 (kiểm tra trích dẫn)";
}

function safeStorage(action: "get" | "set", key: string, value?: string): string | null {
  try {
    if (action === "get") return window.localStorage.getItem(key);
    window.localStorage.setItem(key, value ?? "");
  } catch {
    // Storage can be unavailable (private window, blocked site data); the UI works without it.
  }
  return null;
}

export default function App() {
  const [capabilities, setCapabilities] = useState<Capabilities | null>(null);
  const [health, setHealth] = useState<Health | null>(null);
  const [runs, setRuns] = useState<RunRecord[]>([]);
  const [activeRunId, setActiveRunId] = useState<string | null>(null);
  const [eventsByRun, setEventsByRun] = useState<Record<string, ActivityEvent[]>>({});
  const [query, setQuery] = useState("");
  const [pastedDocument, setPastedDocument] = useState("");
  const [showDocument, setShowDocument] = useState(false);
  const [verificationMode, setVerificationMode] = useState<VerificationMode>("lexical_grounding");
  const [profileId, setProfileId] = useState<string | null>(null);
  const [initializing, setInitializing] = useState(true);
  const [connection, setConnection] = useState<"idle" | "connected" | "disconnected">("idle");
  const [apiError, setApiError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [openSources, setOpenSources] = useState<string[]>([]);
  const [retrievedOpen, setRetrievedOpen] = useState(false);
  const [articles, setArticles] = useState<Record<string, ArticleState>>({});
  const [showSettings, setShowSettings] = useState(false);
  const [theme, setTheme] = useState<"light" | "dark">(() => (safeStorage("get", "luatcheck-theme") === "dark" ? "dark" : "light"));
  const [outboxOpen, setOutboxOpen] = useState(false);
  const [outboxRecipient, setOutboxRecipient] = useState("");
  const [outboxContent, setOutboxContent] = useState("");
  const [proposal, setProposal] = useState<Proposal | null>(null);
  const [outboxMessage, setOutboxMessage] = useState("");
  const [outboxMessageKind, setOutboxMessageKind] = useState<"info" | "success" | "error">("info");
  const [outboxBusy, setOutboxBusy] = useState(false);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [now, setNow] = useState(() => Date.now() / 1000);
  const settingsRef = useRef<HTMLDialogElement>(null);
  const outboxRef = useRef<HTMLDialogElement>(null);
  const runRequestRef = useRef<{ fingerprint: string; key: string } | null>(null);

  const profiles = useMemo(() => capabilities?.profiles ?? [], [capabilities]);
  const activeRun = useMemo(() => runs.find((run) => run.run_id === activeRunId) ?? null, [runs, activeRunId]);
  const currentEvents = activeRunId ? eventsByRun[activeRunId] ?? [] : [];
  const trace = useMemo(() => buildTrace(currentEvents), [currentEvents]);
  const running = activeRun ? activeRun.job_status !== "finished" : false;
  const output = activeRun?.snapshot?.final_output;
  const runProfileId = activeRun?.profile_id ?? activeRun?.snapshot?.profile?.id ?? null;
  const shownProfile: ProfileInfo | null = profiles.find((p) => p.id === (activeRun ? runProfileId ?? profileId : profileId)) ?? profiles[0] ?? null;
  const titles = useMemo(() => {
    const map: Record<string, string> = {};
    for (const step of trace.steps) for (const r of step.results ?? []) if (r.title) map[r.id] = r.title;
    for (const c of output?.citations ?? []) if (c.title) map[c.article_id] = c.title;
    return map;
  }, [trace, output]);

  // live timer only while a run is active
  useEffect(() => {
    if (!running) return;
    const timer = window.setInterval(() => setNow(Date.now() / 1000), 200);
    return () => window.clearInterval(timer);
  }, [running]);

  const elapsedMs = running && activeRun ? Math.max(0, (now - (trace.startedAt ?? activeRun.created_at)) * 1000) : null;

  const loadCurrentRun = useCallback(async (runId: string) => {
    try {
      const updated = await getRun(runId);
      setRuns((previous) => [updated, ...previous.filter((run) => run.run_id !== runId)].sort((a, b) => b.created_at - a.created_at));
    } catch (error) {
      setApiError(error instanceof Error ? error.message : "Không tải được snapshot run.");
    }
  }, []);

  const refreshHealth = useCallback(() => { void getHealth().then(setHealth).catch(() => setHealth(null)); }, []);

  const initializeApp = useCallback(async () => {
    setInitializing(true);
    setApiError("");
    setCapabilities(null);
    try {
      await initialize();
      const [caps, healthNow, history] = await Promise.all([getCapabilities(), getHealth(), listRuns()]);
      setCapabilities(caps);
      setHealth(healthNow);
      setRuns(history.items);
      setProfileId((existing) => existing ?? caps.default_profile ?? caps.profiles?.[0]?.id ?? null);
      if (caps.default_verification_mode) setVerificationMode(caps.default_verification_mode);
      if (!caps.available && caps.reason) setApiError(caps.reason);
    } catch (error) {
      setApiError(error instanceof Error ? error.message : "Không kết nối được với API local.");
      setConnection("disconnected");
    } finally {
      setInitializing(false);
    }
  }, []);

  useEffect(() => { void initializeApp(); }, [initializeApp]);
  useEffect(() => {
    const timer = window.setInterval(refreshHealth, 15000);
    return () => window.clearInterval(timer);
  }, [refreshHealth]);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    safeStorage("set", "luatcheck-theme", theme);
  }, [theme]);

  useEffect(() => {
    if (!activeRunId) return;
    const source = subscribeToRun(activeRunId, (event) => {
      setConnection("connected");
      setEventsByRun((previous) => {
        const existing = previous[activeRunId] ?? [];
        if (event.id !== "" && existing.some((item) => item.id === event.id)) return previous;
        return { ...previous, [activeRunId]: [...existing, event].slice(-200) };
      });
      if (event.event === "run_started") {
        setRuns((previous) => previous.map((run) => run.run_id === activeRunId ? { ...run, job_status: "running", updated_at: event.created_at } : run));
      }
      if (["run_persisted", "run_failed", "run_interrupted"].includes(event.event)) {
        void loadCurrentRun(activeRunId);
        void listRuns().then((history) => setRuns(history.items)).catch(() => undefined);
        refreshHealth();
        source.close();
      }
    }, () => setConnection("disconnected"));
    source.onopen = () => setConnection("connected");
    return () => source.close();
  }, [activeRunId, loadCurrentRun, refreshHealth]);

  useEffect(() => {
    if (showSettings) settingsRef.current?.showModal();
    else settingsRef.current?.close();
  }, [showSettings]);

  useEffect(() => {
    if (outboxOpen) outboxRef.current?.showModal();
    else outboxRef.current?.close();
  }, [outboxOpen]);

  const resetSources = () => { setOpenSources([]); setRetrievedOpen(false); };

  const startNew = () => {
    setActiveRunId(null);
    setQuery("");
    setPastedDocument("");
    resetSources();
    setMobileNavOpen(false);
    setApiError("");
    window.setTimeout(() => document.getElementById("question-input")?.focus(), 0);
  };

  const chooseProfile = (id: string) => {
    setProfileId(id);
    if (activeRunId) startNew();
  };

  const submitQuestion = async (event?: React.FormEvent<HTMLFormElement>) => {
    event?.preventDefault();
    if (!query.trim() || submitting) return;
    if (!capabilities?.available) {
      setApiError(capabilities?.reason || "Backend/corpus chưa sẵn sàng; không thể chạy inference.");
      return;
    }
    setSubmitting(true);
    setApiError("");
    try {
      const fingerprint = JSON.stringify([query.trim(), pastedDocument, verificationMode, profileId]);
      if (!runRequestRef.current || runRequestRef.current.fingerprint !== fingerprint) {
        runRequestRef.current = { fingerprint, key: crypto.randomUUID() };
      }
      const result = await createRun(query.trim(), pastedDocument, verificationMode, runRequestRef.current.key, profileId ?? undefined);
      const created = await getRun(result.run_id).catch((): RunRecord => ({
        run_id: result.run_id, query: query.trim(), verification_mode: verificationMode, job_status: "queued", terminal_status: null,
        profile_id: profileId, created_at: Date.now() / 1000, updated_at: Date.now() / 1000, snapshot: null,
      }));
      setRuns((previous) => [created, ...previous.filter((run) => run.run_id !== result.run_id)]);
      setActiveRunId(result.run_id);
      setEventsByRun((previous) => ({ ...previous, [result.run_id]: [] }));
      resetSources();
      setQuery("");
      setPastedDocument("");
      runRequestRef.current = null;
    } catch (error) {
      setApiError(error instanceof Error ? error.message : "Không gửi được run.");
    } finally {
      setSubmitting(false);
    }
  };

  const chooseHistory = async (run: RunRecord) => {
    setActiveRunId(run.run_id);
    resetSources();
    setMobileNavOpen(false);
    setApiError("");
    await loadCurrentRun(run.run_id);
  };

  const recoverRunInput = async (run: RunRecord) => {
    setQuery(run.query);
    setPastedDocument(run.pasted_document ?? "");
    setVerificationMode(run.snapshot?.verification_mode ?? run.verification_mode);
    if (run.profile_id) setProfileId(run.profile_id);
    setActiveRunId(null);
    resetSources();
    setApiError("");
    if (run.pasted_document === undefined) {
      try {
        const detail = await getRun(run.run_id);
        setPastedDocument((current) => current || detail.pasted_document || "");
      } catch {
        // The saved question remains available for editing even if the API drops again.
      }
    }
    window.setTimeout(() => document.getElementById("question-input")?.focus(), 0);
  };

  const loadArticle = useCallback(async (runId: string, articleId: string) => {
    const key = `${runId}:${articleId}`;
    setArticles((previous) => (previous[key]?.status === "ok" || previous[key]?.status === "loading" ? previous : { ...previous, [key]: { status: "loading" } }));
    try {
      const article = await getArticle(runId, articleId);
      setArticles((previous) => ({ ...previous, [key]: { status: "ok", article } }));
    } catch (error) {
      setArticles((previous) => ({ ...previous, [key]: { status: "error", message: error instanceof Error ? error.message : "Không tải được nguyên văn từ corpus." } }));
    }
  }, []);

  const citedIds = useMemo(() => (output?.citations ?? []).map((c) => c.article_id), [output]);
  const toggleSource = (articleId: string) => {
    if (!activeRun) return;
    const isOpen = openSources.includes(articleId);
    setOpenSources((previous) => (isOpen ? previous.filter((id) => id !== articleId) : [...previous, articleId]));
    if (!isOpen) void loadArticle(activeRun.run_id, articleId);
  };
  const openSource = (articleId: string) => {
    if (!activeRun || running) return;
    if (!citedIds.includes(articleId)) setRetrievedOpen(true);
    setOpenSources((previous) => (previous.includes(articleId) ? previous : [...previous, articleId]));
    void loadArticle(activeRun.run_id, articleId);
  };

  const openOutbox = () => {
    setOutboxRecipient("");
    setOutboxContent(output?.content ?? "");
    setProposal(null);
    setOutboxMessage("");
    setOutboxMessageKind("info");
    setOutboxOpen(true);
  };

  const makeProposal = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!activeRun || outboxBusy) return;
    setOutboxBusy(true);
    setOutboxMessage("");
    setOutboxMessageKind("info");
    try {
      const created = await createProposal(activeRun.run_id, outboxRecipient.trim(), outboxContent);
      setProposal(created);
      if (created.status === "completed") {
        if (["queued_locally", "duplicate_suppressed"].includes(created.result?.status ?? "")) {
          setOutboxMessage(created.result?.status === "duplicate_suppressed"
            ? "Bản tóm tắt này đã có trong hàng đợi cục bộ; chưa gửi email/webhook."
            : "Đã lưu hàng đợi cục bộ; chưa gửi email/webhook.");
          setOutboxMessageKind("success");
        } else {
          setOutboxMessage("API chưa cung cấp receipt outbox có thể xác minh.");
          setOutboxMessageKind("error");
        }
      }
    } catch (error) {
      setOutboxMessage(error instanceof Error ? error.message : "Không tạo được proposal.");
      setOutboxMessageKind("error");
    } finally {
      setOutboxBusy(false);
    }
  };

  const confirmOutbox = async () => {
    if (!proposal || outboxBusy) return;
    setOutboxBusy(true);
    setOutboxMessage("");
    setOutboxMessageKind("info");
    try {
      const result = await confirmProposal(proposal);
      const receipt = result.result;
      if (result.status !== "completed" || !receipt || !["queued_locally", "duplicate_suppressed"].includes(receipt.status ?? "")) {
        throw new Error("API chưa trả receipt xác nhận ghi bền vững vào outbox.");
      }
      setProposal({ ...proposal, status: "completed", result: receipt });
      setOutboxMessage(result.display_message || (receipt.status === "duplicate_suppressed"
        ? "Bản tóm tắt này đã có trong hàng đợi cục bộ; chưa gửi email/webhook."
        : "Đã lưu hàng đợi cục bộ; chưa gửi email/webhook."));
      setOutboxMessageKind("success");
    } catch (error) {
      setOutboxMessage(error instanceof Error ? error.message : "Không xác nhận được proposal.");
      setOutboxMessageKind("error");
      if (error instanceof ApiError && error.status === 409) setProposal({ ...proposal, status: "expired" });
    } finally {
      setOutboxBusy(false);
    }
  };

  const connLabel = initializing ? "Đang kết nối API" : connection === "disconnected" ? "Mất kết nối sự kiện" : "API local";
  const profileName = (id?: string | null) => profiles.find((p) => p.id === id)?.short_name || id || "";
  const retrievedOnly = (activeRun?.snapshot?.retrieved_article_ids ?? []).filter((id) => !citedIds.includes(id));
  const finished = activeRun?.job_status === "finished";
  const terminal: TerminalStatus | null = activeRun?.terminal_status ?? null;

  return (
    <div className="app-shell">
      <header className="mobile-header">
        <button className="icon-button" aria-label="Mở danh sách phiên" onClick={() => setMobileNavOpen((value) => !value)}><Menu size={19} /></button>
        <Brand compact />
        <button className="icon-button" aria-label="Cài đặt" onClick={() => setShowSettings(true)}><Settings2 size={18} /></button>
      </header>

      <aside className={`left-rail ${mobileNavOpen ? "mobile-open" : ""}`}>
        <Brand />
        <button className="new-case-button" onClick={startNew}><Plus size={16} strokeWidth={2.4} /> Câu hỏi mới</button>
        <div className="rail-label"><History size={14} /> GẦN ĐÂY</div>
        <nav className="history-nav" aria-label="Các lượt chạy gần đây">
          {runs.length === 0 ? <div className="history-empty">Các lượt chạy sẽ xuất hiện tại đây.</div> : runs.map((run) => (
            <button key={run.run_id} className={`history-item ${activeRunId === run.run_id ? "active" : ""}`} onClick={() => void chooseHistory(run)}>
              <span className={`hist-icon s-${stateClass(run)}`}><StateIcon run={run} size={14} /></span>
              <span className="history-copy">
                <span className="history-title">{run.query}</span>
                <span className="history-meta">{statusText(run)}{run.snapshot?.elapsed_ms != null ? ` · ${formatDuration(run.snapshot.elapsed_ms)}` : ""}{profiles.length > 1 && run.profile_id ? ` · ${profileName(run.profile_id)}` : ""}</span>
              </span>
            </button>
          ))}
        </nav>
        <div className="rail-spacer" />
        <button className="settings-link" onClick={() => setShowSettings(true)}><Settings2 size={16} /> Cài đặt và cấu hình <ChevronRight size={15} /></button>
        <div className="rail-footer"><ShieldCheck size={14} /> Chạy local · không gửi dữ liệu ra ngoài</div>
      </aside>
      {mobileNavOpen && <button className="mobile-scrim" aria-label="Đóng danh sách" onClick={() => setMobileNavOpen(false)} />}

      <div className="workspace">
        <header className="topbar">
          <div className="topbar-left">
            <span className="topbar-label">Bộ văn bản</span>
            <ProfileSwitch profiles={profiles} value={shownProfile?.id ?? profileId} onChange={chooseProfile} disabled={submitting || running} />
          </div>
          <div className="topbar-actions">
            <span className={`connection-pill ${connection === "connected" ? "online" : connection === "disconnected" ? "offline" : ""}`}><i />{connLabel}</span>
            <button className="icon-button quiet" aria-label="Cài đặt" onClick={() => setShowSettings(true)}><Settings2 size={18} /></button>
          </div>
        </header>
        <SystemStrip capabilities={capabilities} health={health} profile={shownProfile} />

        <main className="main-area">
          {!activeRun ? (
            <div className="welcome-view">
              <div className="welcome-kicker"><span className="kicker-mark"><Scale size={17} /></span> LUATCHECK · TRỢ LÝ HỎI ĐÁP CÓ CĂN CỨ</div>
              <h1>{shownProfile?.short_name ?? "Hỏi đáp có căn cứ"}</h1>
              <p className="welcome-lead">{shownProfile?.scope_note ?? "Đặt câu hỏi; câu trả lời chỉ dựa trên văn bản đã nạp và có trích dẫn để mở nguyên văn đối chiếu."}</p>
              {apiError && <div className="inline-alert error-alert" role="alert"><CircleAlert size={17} /><span>{apiError}</span><button className="retry-button" onClick={() => void initializeApp()}>Thử kết nối lại</button></div>}
              <form className="composer-card" onSubmit={(event) => void submitQuestion(event)}>
                <label className="composer-label" htmlFor="question-input"><span className="composer-dot" /> CÂU HỎI</label>
                <textarea
                  id="question-input" value={query} onChange={(event) => setQuery(event.target.value)} disabled={submitting} maxLength={8000} rows={4} required autoFocus
                  placeholder="Nhập câu hỏi (Enter để gửi, Shift+Enter xuống dòng)"
                  onKeyDown={(event) => {
                    if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) { event.preventDefault(); void submitQuestion(); }
                  }}
                />
                <div className="composer-options">
                  <button type="button" className={`attach-button ${showDocument ? "active" : ""}`} disabled={submitting} onClick={() => setShowDocument((value) => !value)}><FileText size={15} /> {showDocument ? "Ẩn văn bản đính kèm" : "Đính kèm văn bản"}<ChevronDown size={14} /></button>
                  <label className="mode-select-label">KIỂM TRA<select value={verificationMode} disabled={submitting} onChange={(event) => setVerificationMode(event.target.value as VerificationMode)} aria-label="Chế độ kiểm tra">
                    <option value="lexical_grounding">L1: kiểm tra trích dẫn</option>
                    <option value="off">OFF: không kiểm tra</option>
                    {capabilities?.verification_modes.includes("semantic_entailment") && <option value="semantic_entailment">L1 + L2 (semantic)</option>}
                  </select></label>
                </div>
                {showDocument && <label className="document-field">Văn bản bạn cung cấp (coi là dữ liệu không tin cậy)<textarea value={pastedDocument} onChange={(event) => setPastedDocument(event.target.value)} disabled={submitting} maxLength={100000} rows={4} placeholder="Dán nội dung cần tham chiếu." /></label>}
                <div className="composer-bottom"><span><ShieldCheck size={14} /> Câu trả lời đến từ model local đã cấu hình; lỗi backend hiện là lỗi, không có câu trả lời thay thế</span><button type="submit" className="button-primary submit-button" disabled={submitting || !query.trim() || !capabilities?.available}>{submitting ? <LoaderCircle className="spinning" size={16} /> : <Send size={15} />} Gửi câu hỏi</button></div>
                {health?.model.reachable === false && <div className="model-warning" role="status"><CircleAlert size={15} /><span>Model endpoint chưa kết nối. Lượt chạy sẽ trả về lỗi thực thi; hệ thống không tạo câu trả lời thay thế.</span></div>}
                {health?.reranker?.enabled && health.reranker.reachable === false && <div className="model-warning" role="status"><CircleAlert size={15} /><span>Reranker server chưa kết nối. Bước tra cứu sẽ trả về lỗi thực thi (không có fallback thầm lặng).</span></div>}
                {!capabilities?.available && !initializing && <div className="composer-unavailable"><CircleAlert size={14} /> {capabilities?.reason || "Backend hoặc corpus chưa sẵn sàng."}</div>}
              </form>
              {(shownProfile?.suggestions.length ?? 0) > 0 && <>
                <div className="suggestion-heading"><Sparkles size={14} /> CÂU HỎI MẪU (bấm để điền vào ô nhập)</div>
                <div className="suggestions">
                  {shownProfile!.suggestions.map((s) => <button key={s.text} onClick={() => { setQuery(s.text); document.getElementById("question-input")?.focus(); }}>{s.tag && <span className="sugg-tag">{s.tag}</span>}<span className="sugg-text">{s.text}</span><ArrowUpRight size={15} /></button>)}
                </div>
              </>}
              <div className="welcome-footnote"><Info size={14} /> Lượt chạy lưu trong SQLite cục bộ ({capabilities?.web_storage?.retention_days ?? 30} ngày). Đây không phải tư vấn; điểm kiểm tra là proxy từ vựng, không phải độ đúng.</div>
            </div>
          ) : (
            <div className="result-view">
              <div className="run-heading">
                <div className="run-meta-row">
                  <span className={`state-badge state-${stateClass(activeRun)}`}><StateIcon run={activeRun} size={14} />{statusText(activeRun)}</span>
                  {runProfileId && <span className="meta-chip">{profileName(runProfileId)}</span>}
                  <span className="meta-chip">{modeName(activeRun.verification_mode)}</span>
                  <span className="meta-chip faint">{formatClock(activeRun.created_at)}</span>
                  <button className="button-secondary ask-again" onClick={startNew}><Plus size={15} /> Hỏi câu khác</button>
                </div>
                <h1>{activeRun.query}</h1>
              </div>
              {apiError && <div className="inline-alert error-alert" role="alert"><CircleAlert size={17} /><span>{apiError}</span><button onClick={() => setApiError("")} aria-label="Đóng thông báo"><X size={15} /></button></div>}
              <div className="result-grid">
                <div className="result-left">
                  {running && <WorkingCard elapsedMs={elapsedMs} queued={activeRun.job_status === "queued"} message={connection === "disconnected" ? "Mất kết nối sự kiện; lượt chạy vẫn thuộc worker. Tải lại trang để đọc kết quả khi xong." : "Controller local, tra cứu và reranker đang chạy thật trên máy này. Các bước hiện dần ở bảng bên phải."} />}
                  {finished && <SectionErrorBoundary resetKey={activeRun.run_id} onReload={() => void loadCurrentRun(activeRun.run_id)} onRecover={() => void recoverRunInput(activeRun)}>
                    <OutcomeCard run={activeRun} onRetry={() => void recoverRunInput(activeRun)} onOpenOutbox={openOutbox} onOpenSource={(id) => { openSource(id); document.getElementById("sources-anchor")?.scrollIntoView({ behavior: "smooth", block: "start" }); }} />
                  </SectionErrorBoundary>}
                  {finished && !activeRun.snapshot && <div className="inline-alert error-alert"><CircleAlert size={17} /><span>Snapshot chưa có. <button className="text-button" onClick={() => void loadCurrentRun(activeRun.run_id)}>Tải lại</button></span></div>}
                  {finished && activeRun.snapshot && <SectionErrorBoundary resetKey={activeRun.run_id} onReload={() => void loadCurrentRun(activeRun.run_id)} onRecover={() => void recoverRunInput(activeRun)}>
                    <section id="sources-anchor" className="panel sources" aria-label="Căn cứ">
                      <div className="panel-title"><span><BookOpen size={14} /> CĂN CỨ TRÍCH DẪN</span><span className="count-pill">{citedIds.length}</span></div>
                      {citedIds.length === 0 ? <p className="panel-empty">{terminal === "answered" ? "Câu trả lời không có trích dẫn." : "Không có trích dẫn: lượt chạy này không kết thúc bằng câu trả lời."}</p> : <ul className="source-list">
                        {(output?.citations ?? []).map((c, i) => <SourceItem key={`${c.article_id}-${i}`} id={c.article_id} title={c.title || titles[c.article_id] || c.article_id} subtitle={[c.law_name, c.source_pages?.length ? `trang ${c.source_pages.join(", ")}` : ""].filter(Boolean).join(" · ")} quote={c.exact_quote} state={articles[`${activeRun.run_id}:${c.article_id}`]} open={openSources.includes(c.article_id)} onToggle={() => toggleSource(c.article_id)} tag="được trích dẫn" />)}
                      </ul>}
                      {retrievedOnly.length > 0 && <div className="retrieved">
                        <button className="retrieved-toggle" aria-expanded={retrievedOpen} onClick={() => setRetrievedOpen((v) => !v)}>{retrievedOpen ? <ChevronDown size={16} /> : <ChevronRight size={16} />} Mục đã truy xuất nhưng không được trích dẫn <span className="count-pill">{retrievedOnly.length}</span></button>
                        {retrievedOpen && <ul className="source-list">
                          {retrievedOnly.map((id) => <SourceItem key={id} id={id} title={titles[id] || id} state={articles[`${activeRun.run_id}:${id}`]} open={openSources.includes(id)} onToggle={() => toggleSource(id)} tag="đã truy xuất" />)}
                        </ul>}
                      </div>}
                    </section>
                    <Measurements run={activeRun} />
                    <LexicalPanel run={activeRun} />
                  </SectionErrorBoundary>}
                </div>
                <div className="result-right">
                  <Timeline trace={trace} nowMs={elapsedMs} running={running} connection={connection} onOpenSource={(id) => { openSource(id); document.getElementById("sources-anchor")?.scrollIntoView({ behavior: "smooth", block: "start" }); }} searchTool={shownProfile?.search_tool} profileLabel={shownProfile ? `${shownProfile.short_name ?? shownProfile.id} · công cụ ${shownProfile.search_tool} / ${shownProfile.read_tool}` : undefined} />
                </div>
              </div>
            </div>
          )}
        </main>
      </div>

      <dialog className="app-dialog settings-dialog" ref={settingsRef} onClose={() => setShowSettings(false)} onClick={(event) => { if (event.target === settingsRef.current) setShowSettings(false); }}>
        <div className="dialog-heading"><div><span className="panel-kicker">CẤU HÌNH ĐANG CHẠY</span><h2>Cài đặt</h2></div><button className="icon-button" onClick={() => setShowSettings(false)} aria-label="Đóng cài đặt"><X size={18} /></button></div>
        <div className="setting-block"><div><b>Giao diện</b><small>Lưu trên trình duyệt này.</small></div><div className="theme-switch"><button className={theme === "light" ? "active" : ""} onClick={() => setTheme("light")}><Sun size={15} /> Sáng</button><button className={theme === "dark" ? "active" : ""} onClick={() => setTheme("dark")}><Moon size={15} /> Tối</button></div></div>
        <div className="setting-block"><div><b>Model điều khiển</b><small>{capabilities?.model?.endpoint ?? ""}</small></div><span className="setting-value">{capabilities?.model ? `${capabilities.model.name} (${capabilities.model.provider})` : "—"}</span></div>
        <div className="setting-block"><div><b>Trạng thái model</b><small>API có thể sống khi model chưa sẵn sàng.</small></div><span className={`health-value ${health?.model.reachable ? "healthy" : "unhealthy"}`}>{health?.model.reachable ? health.model.configured_model_present ? "Đã kết nối · model có trong danh sách" : "Đã kết nối · chưa thấy model trong danh sách" : "Chưa kết nối"}</span></div>
        <div className="setting-block"><div><b>Reranker</b><small>{shownProfile?.retrieval?.reranker.model ?? ""}</small></div><span className={`health-value ${health?.reranker?.reachable ? "healthy" : "unhealthy"}`}>{health?.reranker?.enabled ? (health.reranker.reachable ? "Đã kết nối" : "Chưa kết nối") : "Không dùng"}</span></div>
        {profiles.map((p) => <div className="setting-block" key={p.id}><div><b>{p.short_name ?? p.id}</b><small>{p.config_file ?? "config mặc định"} · {p.id}</small></div><span className="setting-value">{p.available ? `${p.corpus?.documents ?? "?"} văn bản · ${p.corpus?.records ?? "?"} mục` : `Không khả dụng: ${p.error ?? ""}`}</span></div>)}
        <div className="setting-note"><Info size={15} /> Cấu hình mỗi lượt chạy được lưu cùng lượt chạy. Web DB: {capabilities?.web_storage?.database_location || "data/db/web_ui.sqlite3"} · giữ {capabilities?.web_storage?.retention_days ?? 30} ngày. Giao diện không sửa file YAML.</div>
      </dialog>

      <dialog className="app-dialog outbox-dialog" ref={outboxRef} onClose={() => setOutboxOpen(false)} onClick={(event) => { if (event.target === outboxRef.current) setOutboxOpen(false); }}>
        <div className="dialog-heading"><div><span className="panel-kicker">HÀNG ĐỢI CỤC BỘ</span><h2>{proposal ? "Xem lại nội dung" : "Chuẩn bị bản tóm tắt"}</h2></div><button className="icon-button" onClick={() => setOutboxOpen(false)} aria-label="Đóng"><X size={18} /></button></div>
        {!proposal ? <form onSubmit={(event) => void makeProposal(event)} className="outbox-form">
          <div className="inline-alert info-alert"><Info size={16} /><span>Thao tác này chỉ ghi vào hàng đợi cục bộ. Email/webhook không được gửi.</span></div>
          <label>Người nhận<input value={outboxRecipient} onChange={(event) => setOutboxRecipient(event.target.value)} required maxLength={320} autoComplete="off" placeholder="Tên hoặc email để ghi vào bản nháp" /></label>
          <label>Nội dung chính xác<textarea value={outboxContent} onChange={(event) => setOutboxContent(event.target.value)} required maxLength={40000} rows={8} /></label>
          {outboxMessage && <div className={`inline-alert ${outboxMessageKind}-alert`} role={outboxMessageKind === "error" ? "alert" : "status"}>{outboxMessageKind === "error" ? <CircleAlert size={16} /> : <Info size={16} />}<span>{outboxMessage}</span></div>}
          <div className="dialog-actions"><button type="button" className="button-secondary" onClick={() => setOutboxOpen(false)}>Huỷ</button><button type="submit" className="button-primary" disabled={outboxBusy}>{outboxBusy ? <LoaderCircle className="spinning" size={16} /> : <ArrowDown size={16} />} Xem lại nội dung</button></div>
        </form> : <div className="proposal-review">
          <div className="proposal-recipient"><span>NGƯỜI NHẬN</span><b>{proposal.recipient}</b></div>
          <div className="proposal-body-label">NỘI DUNG SẼ GHI</div><pre className="proposal-content">{proposal.content}</pre>
          <div className="proposal-hash"><span>SHA-256 payload</span><code>{proposal.payload_hash}</code></div>
          {outboxMessage && <div className={`inline-alert ${outboxMessageKind}-alert`} role={outboxMessageKind === "error" ? "alert" : "status"}>{outboxMessageKind === "success" ? <CircleCheck size={16} /> : outboxMessageKind === "error" ? <CircleAlert size={16} /> : <Info size={16} />}<span>{outboxMessage}</span></div>}
          {proposal.status === "pending_confirmation" ? <div className="dialog-actions"><button className="button-secondary" onClick={() => setOutboxOpen(false)}>Để sau</button><button className="button-primary" onClick={() => void confirmOutbox()} disabled={outboxBusy}>{outboxBusy ? <LoaderCircle className="spinning" size={16} /> : <ShieldCheck size={16} />} Xác nhận lưu local</button></div> : proposal.status === "expired" ? <div className="dialog-actions"><button className="button-secondary" onClick={() => setOutboxOpen(false)}>Đóng</button><button className="button-primary" onClick={() => { setProposal(null); setOutboxMessage(""); setOutboxMessageKind("info"); }}>Tạo bản duyệt mới</button></div> : <div className="dialog-actions"><button className="button-primary" onClick={() => setOutboxOpen(false)}><Check size={16} /> Đóng</button></div>}
        </div>}
      </dialog>
    </div>
  );
}

function Brand({ compact = false }: { compact?: boolean }) {
  return <div className={`brand ${compact ? "compact" : ""}`}><span className="brand-icon"><Scale size={18} strokeWidth={2.1} /></span><span><b>LuatCheck</b><small>GROUNDED QA · LOCAL</small></span></div>;
}
