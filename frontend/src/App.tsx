import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Activity, ArrowDown, ArrowUpRight, BookOpen, Check, ChevronDown, ChevronLeft, ChevronRight,
  CircleAlert, CircleCheck, Clock3, FileText, History, Info, LoaderCircle,
  Menu, Moon, Plus, Scale, Search, Send, Settings2, ShieldCheck,
  Sparkles, Sun, X,
} from "lucide-react";
import {
  ApiError, confirmProposal, createProposal, createRun, getArticle, getCapabilities, getHealth,
  getRun, initialize, listRuns, subscribeToRun,
} from "./api";
import { SectionErrorBoundary } from "./ErrorBoundary";
import type {
  ActivityEvent, Article, Capabilities, Proposal, RunRecord, RunSnapshot, TerminalStatus, VerificationMode,
} from "./types";

const suggestions = [
  "Thời gian thử việc tối đa đối với vị trí chuyên môn là bao lâu?",
  "Người lao động cần báo trước bao nhiêu ngày khi đơn phương nghỉ việc?",
  "Tiền lương trong thời gian thử việc được quy định thế nào?",
];

const eventLabels: Record<string, string> = {
  run_queued: "Đã vào hàng đợi",
  run_started: "Core bắt đầu xử lý",
  model_call_started: "Đang chờ inference native",
  tool_completed: "Đã truy xuất căn cứ",
  verification_completed: "Đã chạy bước kiểm tra cấu hình",
  repair_started: "Đang thực hiện lượt sửa chữa",
  run_finished: "Core kết thúc lượt chạy",
  run_persisted: "Đã lưu snapshot",
  run_failed: "Lỗi thực thi",
  run_interrupted: "Run bị gián đoạn khi API khởi động lại",
  summary_proposal_created: "Đã tạo bản nháp hàng đợi cục bộ",
  summary_proposal_completed: "Đã xử lý xác nhận outbox",
};

function timestamp(value?: number) {
  if (!value) return "";
  return new Intl.DateTimeFormat("vi-VN", { hour: "2-digit", minute: "2-digit", day: "2-digit", month: "short" }).format(new Date(value * 1000));
}

function statusText(status: TerminalStatus | null | undefined, job?: string) {
  if (job === "queued") return "Đang xếp hàng";
  if (job === "running") return "Đang xử lý";
  if (status === "answered") return "Đã có câu trả lời";
  if (status === "clarified") return "Cần làm rõ";
  if (status === "refused") return "Từ chối";
  if (status === "error") return "Lỗi thực thi";
  return "Chưa chạy";
}

function StatusMark({ run }: { run: RunRecord }) {
  const state = run.job_status === "queued" || run.job_status === "running" ? "active" : run.terminal_status ?? "error";
  if (state === "active") return <LoaderCircle className="status-icon spinning" aria-label={statusText(run.terminal_status, run.job_status)} />;
  if (state === "answered") return <CircleCheck className="status-icon success" aria-label="Đã có câu trả lời" />;
  if (state === "error" || state === "refused") return <CircleAlert className="status-icon error" aria-label={statusText(run.terminal_status)} />;
  return <Clock3 className="status-icon muted" aria-label={statusText(run.terminal_status)} />;
}

function modeName(mode: VerificationMode | null | undefined) {
  if (!mode) return "Không có dữ liệu";
  if (mode === "off") return "Tắt kiểm tra";
  if (mode === "semantic_entailment") return "Semantic native";
  return "Lexical checks";
}

export default function App() {
  const [capabilities, setCapabilities] = useState<Capabilities | null>(null);
  const [apiHealth, setApiHealth] = useState<Awaited<ReturnType<typeof getHealth>> | null>(null);
  const [runs, setRuns] = useState<RunRecord[]>([]);
  const [activeRunId, setActiveRunId] = useState<string | null>(null);
  const [eventsByRun, setEventsByRun] = useState<Record<string, ActivityEvent[]>>({});
  const [query, setQuery] = useState("");
  const [pastedDocument, setPastedDocument] = useState("");
  const [verificationMode, setVerificationMode] = useState<VerificationMode>("lexical_grounding");
  const [initializing, setInitializing] = useState(true);
  const [connection, setConnection] = useState<"idle" | "connected" | "disconnected">("idle");
  const [apiError, setApiError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [busyMessage, setBusyMessage] = useState("");
  const [openPanel, setOpenPanel] = useState<"references" | "activity" | null>(null);
  const [selectedArticle, setSelectedArticle] = useState<Article | null>(null);
  const [articleLoading, setArticleLoading] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [theme, setTheme] = useState<"light" | "dark">(() => {
    const saved = localStorage.getItem("luatcheck-theme");
    return saved === "dark" ? "dark" : "light";
  });
  const [outboxOpen, setOutboxOpen] = useState(false);
  const [outboxRecipient, setOutboxRecipient] = useState("");
  const [outboxContent, setOutboxContent] = useState("");
  const [proposal, setProposal] = useState<Proposal | null>(null);
  const [outboxMessage, setOutboxMessage] = useState("");
  const [outboxMessageKind, setOutboxMessageKind] = useState<"info" | "success" | "error">("info");
  const [outboxBusy, setOutboxBusy] = useState(false);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const settingsRef = useRef<HTMLDialogElement>(null);
  const outboxRef = useRef<HTMLDialogElement>(null);
  const referencePanelRef = useRef<HTMLElement>(null);
  const referenceTriggerRef = useRef<HTMLButtonElement>(null);
  const mainContentRef = useRef<HTMLElement>(null);
  const leftRailRef = useRef<HTMLElement>(null);
  const topbarRef = useRef<HTMLElement>(null);
  const mobileHeaderRef = useRef<HTMLElement>(null);
  const submitRef = useRef<HTMLButtonElement>(null);
  const runRequestRef = useRef<{ fingerprint: string; key: string } | null>(null);
  const [narrowReferences, setNarrowReferences] = useState(() => window.matchMedia("(max-width: 1240px)").matches);

  const activeRun = useMemo(() => runs.find((run) => run.run_id === activeRunId) ?? null, [runs, activeRunId]);
  const currentEvents = activeRunId ? eventsByRun[activeRunId] ?? [] : [];
  const output = activeRun?.snapshot?.final_output;
  const citations = output?.citations ?? [];
  const eventsConnected = connection === "connected";
  const referenceDrawerOpen = narrowReferences && openPanel === "references";

  useEffect(() => {
    const media = window.matchMedia("(max-width: 1240px)");
    const update = () => setNarrowReferences(media.matches);
    update();
    media.addEventListener("change", update);
    return () => media.removeEventListener("change", update);
  }, []);

  useEffect(() => {
    const panel = referencePanelRef.current;
    if (!referenceDrawerOpen || !panel) return;
    const backgrounds = [mainContentRef.current, leftRailRef.current, topbarRef.current, mobileHeaderRef.current]
      .filter((element): element is HTMLElement => element !== null);
    const previousInert = backgrounds.map((element) => element.inert);
    backgrounds.forEach((element) => { element.inert = true; });
    const focusables = () => Array.from(panel.querySelectorAll<HTMLElement>(
      'a[href], button:not([disabled]), input:not([disabled]), textarea:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])',
    )).filter((element) => element.getClientRects().length > 0);
    panel.querySelector<HTMLElement>(".panel-close")?.focus();
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        setOpenPanel(null);
        setSelectedArticle(null);
        return;
      }
      if (event.key !== "Tab") return;
      const controls = focusables();
      if (!controls.length) {
        event.preventDefault();
        panel.focus();
      } else if (event.shiftKey && document.activeElement === controls[0]) {
        event.preventDefault();
        controls[controls.length - 1].focus();
      } else if (!event.shiftKey && document.activeElement === controls[controls.length - 1]) {
        event.preventDefault();
        controls[0].focus();
      }
    };
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      backgrounds.forEach((element, index) => { element.inert = previousInert[index]; });
      referenceTriggerRef.current?.focus();
    };
  }, [referenceDrawerOpen]);

  useEffect(() => {
    if (referenceDrawerOpen && selectedArticle) {
      referencePanelRef.current?.querySelector<HTMLElement>(".article-reader .back-link")?.focus();
    }
  }, [referenceDrawerOpen, selectedArticle]);

  const loadCurrentRun = useCallback(async (runId: string) => {
    try {
      const updated = await getRun(runId);
      setRuns((previous) => [updated, ...previous.filter((run) => run.run_id !== runId)].sort((a, b) => b.created_at - a.created_at));
    } catch (error) {
      setApiError(error instanceof Error ? error.message : "Không tải được snapshot run.");
    }
  }, []);

  const initializeApp = useCallback(async () => {
    setInitializing(true);
    setApiError("");
    setCapabilities(null);
    setApiHealth(null);
    try {
      await initialize();
      const [caps, health, history] = await Promise.all([getCapabilities(), getHealth(), listRuns()]);
      setCapabilities(caps);
      setApiHealth(health);
      setRuns(history.items);
      if (history.items[0]) setActiveRunId((existing) => existing ?? history.items[0].run_id);
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
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("luatcheck-theme", theme);
  }, [theme]);

  useEffect(() => {
    if (!activeRunId) return;
    const source = subscribeToRun(activeRunId, (event) => {
      setConnection("connected");
      if (event.event === "run_started") {
        setRuns((previous) => previous.map((run) => run.run_id === activeRunId ? { ...run, job_status: "running", updated_at: event.created_at } : run));
        setBusyMessage("Worker đã nhận run; core đang xử lý.");
      } else if (event.event === "model_call_started") {
        setBusyMessage("Đang chờ phản hồi từ inference native.");
      } else if (event.event === "tool_completed") {
        setBusyMessage("Core đã truy xuất căn cứ; xử lý tiếp tục theo luồng thực.");
      } else if (event.event === "verification_completed") {
        setBusyMessage("Đã chạy bước kiểm tra cấu hình.");
      }
      setEventsByRun((previous) => {
        const existing = previous[activeRunId] ?? [];
        if (existing.some((item) => item.id === event.id && item.id !== "")) return previous;
        return { ...previous, [activeRunId]: [...existing, event].slice(-100) };
      });
      if (["run_persisted", "run_failed", "run_interrupted"].includes(event.event)) {
        void loadCurrentRun(activeRunId);
        void listRuns().then((history) => setRuns(history.items)).catch(() => undefined);
        source.close();
      }
    }, () => setConnection("disconnected"));
    source.onopen = () => setConnection("connected");
    return () => source.close();
  }, [activeRunId, loadCurrentRun]);

  useEffect(() => {
    if (showSettings) settingsRef.current?.showModal();
    else settingsRef.current?.close();
  }, [showSettings]);

  useEffect(() => {
    if (outboxOpen) outboxRef.current?.showModal();
    else outboxRef.current?.close();
  }, [outboxOpen]);

  const startNew = () => {
    setActiveRunId(null);
    setQuery("");
    setPastedDocument("");
    setOpenPanel(null);
    setSelectedArticle(null);
    setMobileNavOpen(false);
  };

  const submitQuestion = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!query.trim() || submitting) return;
    if (!capabilities?.available) {
      setApiError(capabilities?.reason || "Backend/corpus chưa sẵn sàng; không thể chạy inference.");
      return;
    }
    setSubmitting(true);
    setApiError("");
    setBusyMessage("");
    try {
      const fingerprint = JSON.stringify([query.trim(), pastedDocument, verificationMode]);
      if (!runRequestRef.current || runRequestRef.current.fingerprint !== fingerprint) {
        runRequestRef.current = { fingerprint, key: crypto.randomUUID() };
      }
      const result = await createRun(query.trim(), pastedDocument, verificationMode, runRequestRef.current.key);
      const created = await getRun(result.run_id).catch((): RunRecord => ({
        run_id: result.run_id,
        query: query.trim(),
        verification_mode: verificationMode,
        job_status: "queued",
        terminal_status: null,
        created_at: Date.now() / 1000,
        updated_at: Date.now() / 1000,
        snapshot: null,
      }));
      setRuns((previous) => [created, ...previous.filter((run) => run.run_id !== result.run_id)]);
      setActiveRunId(result.run_id);
      setEventsByRun((previous) => ({ ...previous, [result.run_id]: [] }));
      setOpenPanel(null);
      setSelectedArticle(null);
      setQuery("");
      setPastedDocument("");
      runRequestRef.current = null;
      setBusyMessage("Run đã được gửi; đang chờ trạng thái thực từ inference.");
    } catch (error) {
      setApiError(error instanceof Error ? error.message : "Không gửi được run.");
    } finally {
      setSubmitting(false);
    }
  };

  const chooseHistory = async (run: RunRecord) => {
    setActiveRunId(run.run_id);
    setOpenPanel(null);
    setSelectedArticle(null);
    setMobileNavOpen(false);
    await loadCurrentRun(run.run_id);
  };

  const recoverRunInput = async (run: RunRecord) => {
    setQuery(run.query);
    setPastedDocument(run.pasted_document ?? "");
    setVerificationMode(run.snapshot?.verification_mode ?? run.verification_mode);
    setActiveRunId(null);
    setOpenPanel(null);
    setSelectedArticle(null);
    setApiError("");
    if (run.pasted_document === undefined) {
      try {
        const detail = await getRun(run.run_id);
        setRuns((previous) => previous.map((item) => item.run_id === detail.run_id ? detail : item));
        setPastedDocument((current) => current || detail.pasted_document || "");
      } catch {
        // The saved question remains available for editing even if the API drops again.
      }
    }
    document.getElementById("question-input")?.focus();
  };

  const openArticle = async (articleId: string) => {
    if (!activeRun) return;
    setArticleLoading(true);
    setSelectedArticle(null);
    setOpenPanel("references");
    try {
      setSelectedArticle(await getArticle(activeRun.run_id, articleId));
    } catch (error) {
      setApiError(error instanceof Error ? error.message : "Không tải được điều luật từ corpus.");
    } finally {
      setArticleLoading(false);
    }
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
      if (created.event_id) setEventsByRun((previous) => ({
        ...previous,
        [activeRun.run_id]: [...(previous[activeRun.run_id] ?? []), {
          id: String(created.event_id), event: "summary_proposal_created", data: { proposal_id: created.proposal_id }, created_at: created.event_created_at ?? Date.now() / 1000,
        }].slice(-100),
      }));
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
      if (result.event_id && activeRunId) setEventsByRun((previous) => ({
        ...previous,
        [activeRunId]: [...(previous[activeRunId] ?? []), {
          id: String(result.event_id), event: "summary_proposal_completed", data: { status: result.result?.status }, created_at: result.event_created_at ?? Date.now() / 1000,
        }].slice(-100),
      }));
      if (activeRunId) await loadCurrentRun(activeRunId);
    } catch (error) {
      setOutboxMessage(error instanceof Error ? error.message : "Không xác nhận được proposal.");
      setOutboxMessageKind("error");
      if (error instanceof ApiError && error.status === 409) {
        setProposal({ ...proposal, status: "expired" });
      }
    } finally {
      setOutboxBusy(false);
    }
  };

  const runButtonLabel = activeRun ? statusText(activeRun.terminal_status, activeRun.job_status) : "Sẵn sàng tra cứu";

  return (
    <div className="app-shell">
      <header className="mobile-header" ref={mobileHeaderRef}>
        <button className="icon-button" aria-label="Mở danh sách phiên" onClick={() => setMobileNavOpen((value) => !value)}><Menu size={19} /></button>
        <Brand compact />
        <button className="icon-button" aria-label="Cài đặt giao diện" onClick={() => setShowSettings(true)}><Settings2 size={18} /></button>
      </header>

      <aside className={`left-rail ${mobileNavOpen ? "mobile-open" : ""}`} ref={leftRailRef}>
        <Brand />
        <button className="new-case-button" onClick={startNew}><Plus size={16} strokeWidth={2.4} /> Tình huống mới</button>
        <div className="rail-label"><History size={14} /> GẦN ĐÂY</div>
        <nav className="history-nav" aria-label="Các phiên gần đây">
          {runs.length === 0 ? <div className="history-empty">Các phiên sẽ xuất hiện tại đây.</div> : runs.map((run) => (
            <button key={run.run_id} className={`history-item ${activeRunId === run.run_id ? "active" : ""}`} onClick={() => void chooseHistory(run)}>
              <StatusMark run={run} />
              <span className="history-copy"><span className="history-title">{run.query}</span><span className="history-meta">{timestamp(run.created_at)} · {statusText(run.terminal_status, run.job_status)}</span></span>
            </button>
          ))}
        </nav>
        <div className="rail-spacer" />
        <div className="scope-chip"><BookOpen size={15} /><span><b>Phạm vi nguồn</b><small>Bộ luật Lao động 2019<br />Văn bản gốc Công báo</small></span></div>
        <button className="settings-link" onClick={() => setShowSettings(true)}><Settings2 size={16} /> Cài đặt giao diện <ChevronRight size={15} /></button>
        <div className="rail-footer"><ShieldCheck size={14} /> Xử lý local · native inference</div>
      </aside>
      {mobileNavOpen && <button className="mobile-scrim" aria-label="Đóng danh sách phiên" onClick={() => setMobileNavOpen(false)} />}

      <div className="workspace">
        <header className="topbar" ref={topbarRef}>
          <div className="breadcrumbs"><span>Không gian làm việc</span><ChevronRight size={14} /><span>{activeRun ? "Tình huống" : "Tra cứu pháp lý"}</span></div>
          <div className="topbar-actions">
            <span className={`connection-pill ${eventsConnected ? "online" : connection === "disconnected" ? "offline" : ""}`}><i />{initializing ? "Đang kết nối API" : connection === "disconnected" ? "Mất kết nối sự kiện" : "API local"}</span>
            <button className="icon-button quiet" aria-label="Cài đặt" onClick={() => setShowSettings(true)}><Settings2 size={17} /></button>
          </div>
        </header>

        <main className="main-grid">
          <section className="main-content" ref={mainContentRef}>
            {!activeRun ? (
              <div className="welcome-view">
                <div className="welcome-kicker"><span className="kicker-mark"><Scale size={17} /></span> LUATCHECK · KHÔNG GIAN PHÁP LÝ</div>
                <h1>Hiểu rõ quyền của bạn,<br /><em>từng điều luật một.</em></h1>
                <p className="welcome-lead">Đặt câu hỏi về lao động. Mỗi câu trả lời được đối chiếu với văn bản nguồn để bạn tự xem lại căn cứ.</p>
                {apiError && <div className="inline-alert error-alert bootstrap-alert" role="alert"><CircleAlert size={17} /><span>{apiError}</span><button className="retry-button" onClick={() => void initializeApp()}>Thử kết nối lại</button></div>}
                <Composer
                  query={query}
                  setQuery={setQuery}
                  pastedDocument={pastedDocument}
                  setPastedDocument={setPastedDocument}
                  verificationMode={verificationMode}
                  setVerificationMode={setVerificationMode}
                  capabilities={capabilities}
                  modelReachable={apiHealth?.model.reachable}
                  submitting={submitting}
                  onSubmit={submitQuestion}
                  submitRef={submitRef}
                />
                <div className="suggestion-heading"><Sparkles size={14} /> BẮT ĐẦU TỪ MỘT CÂU HỎI</div>
                <div className="suggestions">
                  {suggestions.map((suggestion) => <button key={suggestion} onClick={() => { setQuery(suggestion); document.getElementById("question-input")?.focus(); }}>{suggestion}<ArrowUpRight size={14} /></button>)}
                </div>
                <div className="welcome-footnote"><Info size={14} /> Run text và snapshot lưu trong SQLite local trong {capabilities?.web_storage?.retention_days ?? 30} ngày mặc định; lọc thông tin cá nhân chưa đầy đủ.</div>
                <div className="welcome-footnote"><Info size={14} /> Tài liệu nguồn là văn bản gốc năm 2019, không phải bản hợp nhất hiện hành.</div>
              </div>
            ) : (
              <div className="result-view">
                <div className="run-heading">
                  <div className="eyebrow">TÌNH HUỐNG · {timestamp(activeRun.created_at)}</div>
                  <h1>{activeRun.query}</h1>
                  <div className="run-meta-row">
                    <span className={`state-badge state-${activeRun.terminal_status ?? activeRun.job_status}`}><StatusMark run={activeRun} />{runButtonLabel}</span>
                    <span className="mode-label">{modeName(activeRun.verification_mode)}</span>
                    {activeRun.snapshot?.final_output?.from_cache && <span className="mode-label">Kết quả đã kiểm tra từ cache native</span>}
                  </div>
                </div>

                {apiError && <div className="inline-alert error-alert" role="alert"><CircleAlert size={17} /><span>{apiError}</span><button onClick={() => setApiError("")} aria-label="Đóng thông báo"><X size={15} /></button></div>}
                {(activeRun.job_status === "queued" || activeRun.job_status === "running") && (
                  <div className="working-card" role="status"><div className="working-spinner"><LoaderCircle size={21} /></div><div><b>{activeRun.job_status === "queued" ? "Đang chờ worker" : "Đang xử lý tình huống"}</b><p>{connection === "disconnected" ? "Mất kết nối sự kiện. Run vẫn thuộc worker; tải lại để đọc snapshot khi hoàn tất." : busyMessage || "Inference native đang chạy. Thời gian chờ phụ thuộc vào model đã cấu hình."}</p></div><span className="elapsed-dot"><i /><i /><i /></span></div>
                )}

                {activeRun.job_status === "finished" && <SectionErrorBoundary resetKey={activeRun.run_id} onReload={() => void loadCurrentRun(activeRun.run_id)} onRecover={() => void recoverRunInput(activeRun)}>
                  <AnswerCard run={activeRun} output={output} onOpenOutbox={openOutbox} onRecover={() => void recoverRunInput(activeRun)} />
                </SectionErrorBoundary>}

                <div className="content-tabs" role="tablist" aria-label="Chi tiết run">
                  <button role="tab" aria-selected={openPanel !== "activity"} className={openPanel !== "activity" ? "selected" : ""} onClick={() => setOpenPanel(null)}><FileText size={15} /> Kết quả</button>
                  <button role="tab" aria-selected={openPanel === "activity"} className={openPanel === "activity" ? "selected" : ""} onClick={() => setOpenPanel("activity")}><Activity size={15} /> Hoạt động <span className="tab-count">{currentEvents.length || 0}</span></button>
                  <button ref={referenceTriggerRef} className="mobile-source-tab" aria-controls="reference-panel" aria-expanded={referenceDrawerOpen} onClick={() => setOpenPanel("references")}><BookOpen size={15} /> Căn cứ <span className="tab-count">{citations.length}</span></button>
                </div>

                {openPanel === "activity" ? <ActivityTimeline events={currentEvents} connection={connection} /> : (
                  <div className="detail-content">
                    {activeRun.job_status === "finished" && activeRun.snapshot && <SectionErrorBoundary resetKey={activeRun.run_id} onReload={() => void loadCurrentRun(activeRun.run_id)} onRecover={() => void recoverRunInput(activeRun)}><RunDetails run={activeRun} /></SectionErrorBoundary>}
                    {activeRun.job_status === "finished" && !activeRun.snapshot && <div className="empty-state"><CircleAlert size={19} /><p>Snapshot chưa có. Hãy tải lại run để đọc trạng thái đã lưu.</p><button className="text-button" onClick={() => void loadCurrentRun(activeRun.run_id)}>Tải lại snapshot <ArrowUpRight size={14} /></button><button className="text-button" onClick={() => void recoverRunInput(activeRun)}>Chỉnh câu hỏi <ArrowUpRight size={14} /></button></div>}
                    {activeRun.job_status !== "finished" && <ActivityTimeline compact events={currentEvents} connection={connection} />}
                  </div>
                )}
              </div>
            )}
          </section>

          {referenceDrawerOpen && <button className="reference-scrim" aria-label="Đóng căn cứ" onClick={() => { setOpenPanel(null); setSelectedArticle(null); }} />}
          <aside
            id="reference-panel"
            ref={referencePanelRef}
            className={`reference-panel ${openPanel === "references" ? "drawer-open" : ""}`}
            aria-label="Căn cứ và kiểm tra"
            aria-labelledby="reference-panel-title"
            role={referenceDrawerOpen ? "dialog" : undefined}
            aria-modal={referenceDrawerOpen ? true : undefined}
            tabIndex={referenceDrawerOpen ? -1 : undefined}
          >
            <div className="reference-header"><div><span className="panel-kicker">CĂN CỨ & KIỂM TRA</span><h2 id="reference-panel-title">{selectedArticle ? selectedArticle.title : "Nguồn tham chiếu"}</h2></div><button className="icon-button panel-close" aria-label="Đóng căn cứ" onClick={() => { setOpenPanel(null); setSelectedArticle(null); }}><X size={17} /></button></div>
            <div className="source-banner"><BookOpen size={17} /><span><b>Bộ luật Lao động 2019</b><small>Văn bản gốc Công báo · phạm vi trích dẫn</small></span></div>
            {selectedArticle ? (
              <ArticleReader article={selectedArticle} loading={articleLoading} onBack={() => setSelectedArticle(null)} />
            ) : activeRun ? (
              <>
                <section className="panel-section">
                  <div className="section-title"><span>TRÍCH DẪN TRONG RUN</span><span className="count-pill">{citations.length}</span></div>
                  {citations.length === 0 ? <div className="panel-empty"><BookOpen size={17} /><p>Run này chưa có điều luật được trích dẫn.</p></div> : <div className="citation-list">
                    {citations.map((citation, index) => <button className="citation-card" key={`${citation.article_id}-${index}`} onClick={() => void openArticle(citation.article_id)}>
                      <span className="citation-number">{String(index + 1).padStart(2, "0")}</span><span className="citation-copy"><b>{citation.title || citation.article_id}</b><small>{citation.article_id} · {citation.source_pages?.length ? `trang ${citation.source_pages.join(", ")}` : "mở văn bản nguồn"}</small>{citation.exact_quote && <em>“{citation.exact_quote}”</em>}</span><ChevronRight size={15} />
                    </button>)}
                  </div>}
                </section>
                <LexicalPanel run={activeRun} />
                <div className="source-scope"><Info size={14} /><p>Nguồn là <b>văn bản gốc Bộ luật Lao động 2019</b>. Giao diện không khẳng định văn bản đã được hợp nhất/cập nhật đến năm 2026.</p></div>
              </>
            ) : (
              <div className="reference-empty"><div className="reference-empty-icon"><BookOpen size={22} /></div><b>Căn cứ sẽ hiển thị ở đây</b><p>Khi có run, các điều luật được viện dẫn sẽ liên kết tới đúng nội dung và provenance trong corpus.</p></div>
            )}
            <div className="panel-footer"><ShieldCheck size={14} /> Lexical checks là proxy từ vựng, không chứng nhận độ đúng pháp lý.</div>
          </aside>
        </main>
      </div>

      <dialog className="app-dialog settings-dialog" ref={settingsRef} onClose={() => setShowSettings(false)} onClick={(event) => { if (event.target === settingsRef.current) setShowSettings(false); }}>
        <div className="dialog-heading"><div><span className="panel-kicker">TÙY CHỈNH GIAO DIỆN</span><h2>Cài đặt</h2></div><button className="icon-button" onClick={() => setShowSettings(false)} aria-label="Đóng cài đặt"><X size={18} /></button></div>
        <div className="setting-block"><div><b>Giao diện</b><small>Tuỳ chọn được lưu trên trình duyệt này.</small></div><div className="theme-switch"><button className={theme === "light" ? "active" : ""} onClick={() => setTheme("light")}><Sun size={15} /> Sáng</button><button className={theme === "dark" ? "active" : ""} onClick={() => setTheme("dark")}><Moon size={15} /> Tối</button></div></div>
        <div className="setting-block"><div><b>Inference backend</b><small>Phản hồi luôn đến từ backend đã cấu hình.</small></div><span className="setting-value">{capabilities?.model ? `${capabilities.model.provider} · ${capabilities.model.name}` : "Không có dữ liệu"}</span></div>
        <div className="setting-block"><div><b>Trạng thái model</b><small>API có thể sống trong khi model chưa sẵn sàng.</small></div><span className={`health-value ${apiHealth?.model.reachable ? "healthy" : "unhealthy"}`}>{apiHealth?.model.reachable ? apiHealth.model.configured_model_present ? "Đã kết nối · model có trong danh sách" : "Đã kết nối · model chưa thấy trong danh sách" : "Chưa kết nối"}</span></div>
        <div className="setting-note"><Info size={15} /> Cấu hình cho mỗi run được lưu cùng run. Web database: {capabilities?.web_storage?.database_location || "data/db/web_ui.sqlite3"} · retention {capabilities?.web_storage?.retention_days ?? 30} ngày. Giao diện không sửa file YAML.</div>
      </dialog>

      <dialog className="app-dialog outbox-dialog" ref={outboxRef} onClose={() => setOutboxOpen(false)} onClick={(event) => { if (event.target === outboxRef.current) setOutboxOpen(false); }}>
        <div className="dialog-heading"><div><span className="panel-kicker">HÀNG ĐỢI CỤC BỘ</span><h2>{proposal ? "Xem lại nội dung" : "Chuẩn bị bản tóm tắt"}</h2></div><button className="icon-button" onClick={() => setOutboxOpen(false)} aria-label="Đóng"><X size={18} /></button></div>
        {!proposal ? <form onSubmit={(event) => void makeProposal(event)} className="outbox-form">
          <div className="inline-alert info-alert"><Info size={16} /><span>Thao tác này chỉ ghi vào hàng đợi cục bộ. Email/webhook chưa được gửi.</span></div>
          <label>Người nhận<input value={outboxRecipient} onChange={(event) => setOutboxRecipient(event.target.value)} required maxLength={320} autoComplete="email" placeholder="Tên hoặc email để ghi vào bản nháp" /></label>
          <label>Nội dung chính xác<textarea value={outboxContent} onChange={(event) => setOutboxContent(event.target.value)} required maxLength={40000} rows={8} /></label>
          {outboxMessage && <div className={`inline-alert ${outboxMessageKind}-alert`} role={outboxMessageKind === "error" ? "alert" : "status"}>{outboxMessageKind === "error" ? <CircleAlert size={16} /> : <Info size={16} />}<span>{outboxMessage}</span></div>}
          <div className="dialog-actions"><button type="button" className="button-secondary" onClick={() => setOutboxOpen(false)}>Huỷ</button><button type="submit" className="button-primary" disabled={outboxBusy}>{outboxBusy ? <LoaderCircle className="spinning" size={16} /> : <ArrowDown size={16} />} Xem lại nội dung</button></div>
        </form> : <div className="proposal-review">
          <div className="proposal-recipient"><span>NGƯỜI NHẬN</span><b>{proposal.recipient}</b></div>
          <div className="proposal-body-label">NỘI DUNG SẼ GHI</div><pre className="proposal-content">{proposal.content}</pre>
          <div className="proposal-hash"><span>SHA-256 payload</span><code>{proposal.payload_hash}</code></div>
          {outboxMessage && <div className={`inline-alert ${outboxMessageKind}-alert`} role={outboxMessageKind === "error" ? "alert" : "status"}>{outboxMessageKind === "success" ? <CircleCheck size={16} /> : outboxMessageKind === "error" ? <CircleAlert size={16} /> : <Info size={16} />}<span>{outboxMessage}</span></div>}
          {proposal.status === "pending_confirmation" ? <div className="dialog-actions"><button className="button-secondary" onClick={() => setOutboxOpen(false)}>Để sau</button><button className="button-primary" onClick={() => void confirmOutbox()} disabled={outboxBusy}>{outboxBusy ? <LoaderCircle className="spinning" size={16} /> : <ShieldCheck size={16} />} Xác nhận lưu local</button></div> : proposal.status === "expired" ? <div className="dialog-actions"><button className="button-secondary" onClick={() => setOutboxOpen(false)}>Đóng</button><button className="button-primary" onClick={() => { setProposal(null); setOutboxMessage(""); setOutboxMessageKind("info"); }}>Tạo bản duyệt mới</button></div> : <div className="dialog-actions"><button className="button-primary" onClick={() => setOutboxOpen(false)}>Đóng receipt</button></div>}
        </div>}
      </dialog>
    </div>
  );
}

function Brand({ compact = false }: { compact?: boolean }) {
  return <div className={`brand ${compact ? "compact" : ""}`}><span className="brand-icon"><Scale size={18} strokeWidth={2.1} /></span><span><b>LuatCheck</b><small>LEGAL WORKSPACE</small></span></div>;
}

function Composer({
  query, setQuery, pastedDocument, setPastedDocument, verificationMode, setVerificationMode,
  capabilities, modelReachable, submitting, onSubmit, submitRef,
}: {
  query: string; setQuery: (value: string) => void; pastedDocument: string; setPastedDocument: (value: string) => void;
  verificationMode: VerificationMode; setVerificationMode: (value: VerificationMode) => void;
  capabilities: Capabilities | null; modelReachable: boolean | null | undefined; submitting: boolean; onSubmit: (event: React.FormEvent<HTMLFormElement>) => void;
  submitRef: React.Ref<HTMLButtonElement>;
}) {
  const [showDocument, setShowDocument] = useState(false);
  return <form className="composer-card" onSubmit={onSubmit}>
    <label className="composer-label" htmlFor="question-input"><span className="composer-dot" /> MÔ TẢ TÌNH HUỐNG CỦA BẠN</label>
    <textarea id="question-input" value={query} onChange={(event) => setQuery(event.target.value)} disabled={submitting} maxLength={8000} rows={4} required placeholder="Ví dụ: Công ty thông báo chấm dứt hợp đồng của tôi sau 2 năm làm việc. Tôi cần lưu ý điều gì?" />
    <div className="composer-options"><button type="button" className={`attach-button ${showDocument ? "active" : ""}`} disabled={submitting} onClick={() => setShowDocument((value) => !value)}><FileText size={15} /> {showDocument ? "Ẩn văn bản" : "Thêm văn bản"}<ChevronDown size={14} /></button><label className="mode-select-label">KIỂM TRA<select value={verificationMode} disabled={submitting} onChange={(event) => setVerificationMode(event.target.value as VerificationMode)} aria-label="Chế độ kiểm tra">
      <option value="off">Tắt</option><option value="lexical_grounding">Lexical checks</option>{capabilities?.verification_modes.includes("semantic_entailment") && <option value="semantic_entailment">Semantic native</option>}
    </select></label></div>
    {showDocument && <label className="document-field">Văn bản hoặc hợp đồng bạn cung cấp<textarea value={pastedDocument} onChange={(event) => setPastedDocument(event.target.value)} disabled={submitting} maxLength={100000} rows={5} placeholder="Dán nội dung cần tham chiếu. Đây là dữ liệu do bạn cung cấp." /></label>}
    <div className="composer-bottom"><span><ShieldCheck size={14} /> Chạy qua model native đã cấu hình</span><button ref={submitRef} type="submit" className="button-primary submit-button" disabled={submitting || !query.trim() || !capabilities?.available}>{submitting ? <LoaderCircle className="spinning" size={16} /> : <Send size={15} />} Phân tích tình huống <ArrowUpRight size={14} /></button></div>
    {modelReachable === false && <div className="model-warning" role="status"><CircleAlert size={14} /><span>Model endpoint chưa kết nối. Run được gửi sẽ trả lỗi thực thi nếu dependency chưa sẵn sàng; hệ thống không tạo câu trả lời thay thế.</span></div>}
    {!capabilities?.available && <div className="composer-unavailable"><CircleAlert size={14} /> {capabilities?.reason || "Đang kiểm tra backend và corpus…"}</div>}
  </form>;
}

function AnswerCard({ run, output, onOpenOutbox, onRecover }: { run: RunRecord; output: RunSnapshot["final_output"] | undefined; onOpenOutbox: () => void; onRecover: () => void }) {
  if (run.terminal_status === "error") return <div className="result-card terminal-error"><div className="result-heading"><span className="result-icon error"><CircleAlert size={17} /></span><div><b>Lỗi thực thi</b><small>Không có câu trả lời thay thế được tạo.</small></div></div><p>{output?.reason || "Inference hoặc một dependency đã gặp lỗi. Kiểm tra trạng thái API/model trong cài đặt."}</p>{output?.error_kind && <code className="error-kind">{output.error_kind}</code>}<div className="recovery-actions"><button className="button-secondary" onClick={onRecover}>Chỉnh câu hỏi rồi chạy lại</button></div></div>;
  if (run.terminal_status === "refused") return <div className="result-card terminal-refused"><div className="result-heading"><span className="result-icon warning"><ShieldCheck size={17} /></span><div><b>Chưa thể trả lời</b><small>Kết luận từ core LuatCheck</small></div></div><p>{output?.reason || "Core không đưa ra câu trả lời có căn cứ."}</p><div className="recovery-actions"><button className="button-secondary" onClick={onRecover}>Chỉnh câu hỏi hoặc văn bản</button></div></div>;
  if (run.terminal_status === "clarified") return <div className="result-card terminal-clarified"><div className="result-heading"><span className="result-icon info"><Info size={17} /></span><div><b>Cần thêm thông tin</b><small>Core yêu cầu làm rõ trước khi trả lời</small></div></div><p>{output?.question}</p><div className="recovery-actions"><button className="button-secondary" onClick={onRecover}>Chỉnh câu hỏi hoặc văn bản</button></div></div>;
  if (run.terminal_status !== "answered") return null;
  return <article className="result-card answer-card">
    <div className="answer-topline"><div className="result-heading"><span className="result-icon success"><Check size={17} /></span><div><b>Câu trả lời</b><small>{output?.verified ? "Đã qua bước kiểm tra được cấu hình" : "Đã trả về từ model native · chưa bật kiểm tra"}</small></div></div><button className="export-button" onClick={onOpenOutbox}><Send size={14} /> Lưu bản tóm tắt</button></div>
    <div className="answer-content">{output?.content}</div>
    <div className="answer-disclaimer"><Info size={14} /><span>Đây là thông tin tham khảo dựa trên nguồn được liệt kê. Lexical checks là proxy từ vựng, không xác nhận nội dung tư vấn đúng pháp lý.</span></div>
  </article>;
}

function RunDetails({ run }: { run: RunRecord }) {
  const snapshot = run.snapshot;
  if (!snapshot) return null;
  const usages = [
    ["Lượt gọi model", snapshot.usage?.model_call_count],
    ["Input tokens", snapshot.usage?.input_tokens],
    ["Output tokens", snapshot.usage?.output_tokens],
    ["Model wall time", snapshot.usage?.model_wall_ms == null ? null : `${snapshot.usage.model_wall_ms} ms`],
  ] as const;
  return <div className="run-details">
    {snapshot.grounding && <div className="lexical-summary-card"><div className="summary-title"><span><Search size={15} /> ĐỐI SOÁT TỪ VỰNG</span><span className="proxy-tag">LEXICAL PROXY</span></div><div className="lexical-ratio"><b>{snapshot.grounding.grounded_ratio == null ? "Không có dữ liệu" : `${Math.round(snapshot.grounding.grounded_ratio * 100)}%`}</b><span>số câu qua ngưỡng lexical của analyzer</span></div><div className="lexical-meter"><i style={{ width: `${Math.max(0, Math.min(100, (snapshot.grounding.grounded_ratio ?? 0) * 100))}%` }} /></div><p>Không phải xác suất hay điểm đúng pháp lý.</p></div>}
    <div className="budget-card"><div className="section-title"><span>NGÂN SÁCH RUN</span><span className="mode-label">{modeName(snapshot.verification_mode)}</span></div><div className="budget-grid">
      {snapshot.budgets ? <><BudgetItem label="Tool calls" used={snapshot.budgets.tool_calls.used} limit={snapshot.budgets.tool_calls.limit} /><BudgetItem label="Sửa chữa" used={snapshot.budgets.repairs.used} limit={snapshot.budgets.repairs.limit} /><BudgetItem label="Bước" used={snapshot.budgets.steps.used} limit={snapshot.budgets.steps.limit} /></> : <span className="muted-text">Không có dữ liệu ngân sách.</span>}
    </div></div>
    <div className="usage-card"><div className="section-title"><span>ĐO ĐẠC THỰC TẾ</span>{snapshot.elapsed_ms != null && <span>{snapshot.elapsed_ms} ms tổng run</span>}</div><div className="usage-grid">{usages.map(([label, value]) => <div key={label}><small>{label}</small><b>{value == null ? "Không có dữ liệu" : value}</b></div>)}</div></div>
    <div className="retrieved-row"><span>Điều luật đã truy xuất</span><span>{snapshot.retrieved_article_ids?.length ? snapshot.retrieved_article_ids.join(" · ") : "Không có dữ liệu"}</span></div>
  </div>;
}

function BudgetItem({ label, used, limit }: { label: string; used: number; limit: number }) {
  const ratio = limit > 0 ? Math.min(100, (used / limit) * 100) : 0;
  return <div className="budget-item"><div><span>{label}</span><b>{used}<small> / {limit}</small></b></div><div className="budget-meter"><i style={{ width: `${ratio}%` }} /></div></div>;
}

function LexicalPanel({ run }: { run: RunRecord }) {
  const grounding = run.snapshot?.grounding;
  return <section className="panel-section lexical-panel"><div className="section-title"><span>LEXICAL CHECKS</span><Info size={14} /></div>
    {grounding ? <><div className="lexical-panel-value"><b>{grounding.grounded_ratio == null ? "—" : `${Math.round(grounding.grounded_ratio * 100)}%`}</b><span>lexical proxy</span></div><p>Đo độ trùng lặp từ vựng với điều luật được trích dẫn; không phải điểm chính xác pháp lý.</p><div className="mini-checks"><span><Check size={13} /> Kiểm tra citation ID</span><span><Check size={13} /> Kiểm tra lexical overlap</span></div></> : <div className="panel-empty"><Search size={16} /><p>{run.job_status === "finished" ? "Không có phép đo lexical cho trạng thái này." : "Kiểm tra sẽ hiển thị sau khi run hoàn tất."}</p></div>}
  </section>;
}

function ArticleReader({ article, loading, onBack }: { article: Article | null; loading: boolean; onBack: () => void }) {
  if (loading) return <div className="article-loading"><LoaderCircle className="spinning" size={18} /> Đang đọc corpus…</div>;
  if (!article) return null;
  return <div className="article-reader"><button className="back-link" onClick={onBack}><ChevronLeft size={15} /> Danh sách trích dẫn</button><div className="article-id">{article.article_id}</div><h3>{article.title}</h3><p className="article-law-name">{article.law_name}</p><div className="article-text">{article.content}</div><div className="provenance-card"><div className="provenance-title"><ShieldCheck size={15} /> PROVENANCE TRONG CORPUS</div>{article.scope && <p>{article.scope}</p>}{article.source_pages?.length ? <p>Trang Công báo: {article.source_pages.join(", ")}</p> : null}{article.extraction && <p>Trích xuất: {article.extraction}</p>}{article.source_sha256 && <p className="hash-line">SHA-256 <code>{article.source_sha256}</code></p>}{article.source_url && <a href={article.source_url} target="_blank" rel="noreferrer">Mở PDF nguồn <ArrowUpRight size={13} /></a>}</div></div>;
}

function ActivityTimeline({ events, connection, compact = false }: { events: ActivityEvent[]; connection: string; compact?: boolean }) {
  const hasFinished = events.some((event) => ["run_persisted", "run_failed", "run_interrupted"].includes(event.event));
  return <div className={`activity-panel ${compact ? "compact" : ""}`}>
    <div className="activity-heading"><div><span className="panel-kicker">EVENTS ĐƯỢC QUAN SÁT</span><h3>Hoạt động của run</h3></div><span className={`event-connection ${connection === "disconnected" ? "lost" : ""}`}><i />{connection === "disconnected" ? "Mất kết nối" : hasFinished ? "Đã lưu" : "Đang theo dõi"}</span></div>
    {events.length === 0 ? <div className="activity-empty"><Activity size={20} /><p>Chưa nhận được sự kiện. Khi worker có cập nhật, timeline sẽ hiện các ranh giới thực thi.</p></div> : <ol className="timeline-list">
      {events.map((event, index) => <li key={`${event.id || event.event}-${index}`} className={event.event === "run_failed" || event.event === "run_interrupted" ? "timeline-error" : ""}>
        <span className="timeline-point">{event.event === "run_failed" ? <CircleAlert size={14} /> : event.event === "run_persisted" ? <Check size={14} /> : <i />}</span><div className="timeline-copy"><b>{eventLabels[event.event] || event.event}</b><small>{timestamp(event.created_at)}</small>{event.event === "model_call_started" && typeof event.data.step === "number" && <p>Bước {event.data.step}</p>}{event.event === "tool_completed" && <p>{String(event.data.tool ?? "tool")} · {String(event.data.result_count ?? 0)} kết quả{Array.isArray(event.data.article_ids) && event.data.article_ids.length > 0 ? ` · ${event.data.article_ids.join(", ")}` : ""}</p>}{event.event === "verification_completed" && <p>{String(event.data.mode ?? "")} · {event.data.passed ? "qua kiểm tra cấu hình" : "cần sửa chữa"}</p>}{event.event === "run_persisted" && <p>Trạng thái cuối: {String(event.data.terminal_status ?? "—")}</p>}{event.event === "run_failed" && <p>Loại lỗi: {String(event.data.error_kind ?? "execution_error")}</p>}</div>
      </li>)}
    </ol>}
    <div className="activity-privacy"><ShieldCheck size={14} /> Timeline chỉ hiển thị sự kiện vận hành, không hiển thị chain-of-thought.</div>
  </div>;
}
