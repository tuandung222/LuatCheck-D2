import { useEffect, useRef, type ReactNode } from "react";
import {
  ArrowUpRight, BookOpen, Check, ChevronDown, ChevronRight, CircleAlert, CircleHelp, FileSearch, Info, LoaderCircle, Send, ShieldAlert, ShieldCheck, Ban,
} from "lucide-react";
import { formatCount, formatDuration } from "./format";
import type { Article, RunRecord } from "./types";

export type ArticleState = { status: "loading" } | { status: "error"; message: string } | { status: "ok"; article: Article };

// --------------------------------------------------------------------------- text formatting helper (inline **bold**)

export function renderFormattedText(text?: string | null): ReactNode {
  if (!text) return null;
  const parts = text.split(/(\*\*[^*]+?\*\*)/g);
  if (parts.length === 1) return text;
  return parts.map((part, index) => {
    if (part.startsWith("**") && part.endsWith("**") && part.length > 4) {
      return <strong key={index}>{part.slice(2, -2)}</strong>;
    }
    return part;
  });
}

// --------------------------------------------------------------------------- outcome (one visual state per terminal state)

export function OutcomeCard({ run, onRetry, onOpenOutbox, onOpenSource }: {
  run: RunRecord; onRetry: () => void; onOpenOutbox: () => void; onOpenSource: (id: string) => void;
}) {
  const snapshot = run.snapshot;
  const output = snapshot?.final_output;
  const status = run.terminal_status;
  if (status === "error") {
    return <article className="outcome outcome-error" role="alert">
      <header><span className="outcome-icon"><CircleAlert size={22} /></span><div><b>Lỗi thực thi</b><small>Đây không phải câu trả lời và cũng không phải từ chối. Không có nội dung thay thế nào được tạo.</small></div></header>
      <p className="outcome-text">{renderFormattedText(output?.reason || "Một thành phần (model, reranker hoặc dữ liệu) đã gặp lỗi.")}</p>
      <div className="outcome-foot">{output?.error_kind && <code>{output.error_kind}</code>}<button className="button-secondary" onClick={onRetry}>Chỉnh câu hỏi và chạy lại</button></div>
    </article>;
  }
  if (status === "refused") {
    const kind = snapshot?.refusal_kind ?? (output?.pre_model_policy_refusal ? "guardrail" : "model");
    if (kind === "guardrail") {
      return <article className="outcome outcome-guardrail">
        <header><span className="outcome-icon"><ShieldAlert size={22} /></span><div><b>Bị chặn bởi guardrail</b><small>Chặn trước khi gọi model: không có lệnh gọi model, không có tra cứu.</small></div></header>
        <p className="outcome-text">{renderFormattedText(output?.reason)}</p>
        <div className="outcome-foot"><button className="button-secondary" onClick={onRetry}>Hỏi câu khác</button></div>
      </article>;
    }
    return <article className="outcome outcome-refused">
      <header><span className="outcome-icon"><Ban size={22} /></span><div><b>{kind === "verification_failed" ? "Từ chối: kiểm tra L1 không đạt" : "Từ chối: nguồn không đủ căn cứ"}</b><small>{kind === "verification_failed" ? "Câu trả lời nháp bị bộ kiểm tra bác sau khi hết lượt sửa chữa, nên không được hiển thị như một câu trả lời." : "Hệ thống không đưa ra câu trả lời thay vì suy đoán ngoài các văn bản đã nạp."}</small></div></header>
      <p className="outcome-text">{renderFormattedText(output?.reason)}</p>
      <div className="outcome-foot"><button className="button-secondary" onClick={onRetry}>Chỉnh câu hỏi</button></div>
    </article>;
  }
  if (status === "clarified") {
    return <article className="outcome outcome-clarify">
      <header><span className="outcome-icon"><CircleHelp size={22} /></span><div><b>Cần làm rõ thêm</b><small>Hệ thống hỏi lại thay vì trả lời; chưa có kết luận nào.</small></div></header>
      <p className="outcome-text">{renderFormattedText(output?.question)}</p>
      <div className="outcome-foot"><button className="button-secondary" onClick={onRetry}>Chỉnh câu hỏi</button></div>
    </article>;
  }
  if (status !== "answered") return null;
  const citations = output?.citations ?? [];
  return <article className="outcome outcome-answer">
    <header>
      <span className="outcome-icon"><Check size={22} /></span>
      <div><b>Câu trả lời</b><small>{output?.verified ? "Đã qua kiểm tra L1: trích dẫn tồn tại, đã được truy xuất, trùng từ vựng, số liệu khớp nguồn." : "Chế độ OFF: câu trả lời chưa được kiểm tra."}</small></div>
      <button className="button-ghost" onClick={onOpenOutbox}><Send size={14} /> Lưu bản tóm tắt</button>
    </header>
    <div className="answer-text">{renderFormattedText(output?.content)}</div>
    {citations.length > 0 && <div className="answer-cites"><span>Căn cứ</span>{citations.map((c, i) => <button key={`${c.article_id}-${i}`} onClick={() => onOpenSource(c.article_id)} title="Mở nguyên văn"><BookOpen size={13} />{c.article_id}</button>)}</div>}
    <p className="answer-note"><Info size={14} /> Thông tin tham khảo dựa trên các mục được liệt kê. Kiểm tra L1 là proxy từ vựng, không xác nhận độ đúng của nội dung.</p>
  </article>;
}

export function WorkingCard({ elapsedMs, queued, message }: { elapsedMs: number | null; queued: boolean; message: string }) {
  return <div className="working" role="status">
    <span className="working-icon"><LoaderCircle size={22} /></span>
    <div><b>{queued ? "Đang chờ worker" : "Đang xử lý bằng model local"}</b><p>{message}</p></div>
    <span className="working-timer">{formatDuration(elapsedMs)}</span>
  </div>;
}

// --------------------------------------------------------------------------- source text with the quote highlighted

function escapeRegExp(value: string) { return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"); }

function highlight(content: string, quote?: string | null): { node: ReactNode; found: boolean } {
  if (!quote || !quote.trim()) return { node: content, found: false };
  const pattern = quote.trim().split(/\s+/).map(escapeRegExp).join("\\s+");
  const match = new RegExp(pattern).exec(content);
  if (!match) return { node: content, found: false };
  return { node: <>{content.slice(0, match.index)}<mark data-quote>{match[0]}</mark>{content.slice(match.index + match[0].length)}</>, found: true };
}

export function parseDocCodeFromArticleId(id: string): string {
  const parts = id.split("_");
  if (id.startsWith("HCMUT_") && parts.length >= 2) {
    return parts[1];
  }
  if (parts.length >= 2) {
    if (parts[0].startsWith("ND") || parts[0].startsWith("TT") || parts[0].startsWith("LCD") || parts[0].startsWith("LVL")) {
      return `${parts[0]}_${parts[1]}`;
    }
    return parts[0];
  }
  return id;
}

export function SourceItem({ id, title, subtitle, quote, state, open, onToggle, tag, onInspectPdfChunk }: {
  id: string; title: string; subtitle?: string; quote?: string | null; state?: ArticleState; open: boolean; onToggle: () => void; tag?: string;
  onInspectPdfChunk?: (docCode: string, articleId: string) => void;
}) {
  const ref = useRef<HTMLLIElement>(null);
  const article = state?.status === "ok" ? state.article : null;
  const rendered = article ? highlight(article.content, quote) : null;
  useEffect(() => {
    if (!open) return;
    const el = ref.current;
    if (!el) return;
    el.scrollIntoView({ block: "nearest", behavior: "smooth" });
    const mark = el.querySelector("mark[data-quote]");
    if (mark) mark.scrollIntoView({ block: "center" });
  }, [open, state?.status]);
  return <li ref={ref} className={`source-item ${open ? "open" : ""}`} data-source-id={id}>
    <button className="source-head" aria-expanded={open} onClick={onToggle}>
      {open ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
      <span className="source-main"><b>{title || id}</b><small>{id}{subtitle ? ` · ${subtitle}` : ""}</small></span>
      {tag && <span className="source-tag">{tag}</span>}
    </button>
    {open && <div className="source-body">
      {state?.status === "loading" && <p className="source-loading"><LoaderCircle size={16} className="spinning" /> Đang đọc corpus…</p>}
      {state?.status === "error" && <p className="source-error"><CircleAlert size={15} /> {state.message}</p>}
      {article && <>
        {quote ? (rendered?.found ? <p className="quote-status ok"><Check size={14} /> Đoạn trích của câu trả lời khớp nguyên văn với nguồn (được tô sáng bên dưới).</p> : <p className="quote-status warn"><Info size={14} /> Đoạn trích của model không tìm thấy trong nguồn theo cách so khớp nguyên văn.</p>) : null}
        <div className="source-text">{rendered?.node ?? article.content}</div>
        <dl className="provenance">
          <dt>Văn bản</dt><dd>{article.law_name || "—"}</dd>
          {article.source_pages?.length ? <><dt>Trang</dt><dd>{article.source_pages.join(", ")}</dd></> : null}
          {article.scope ? <><dt>Phạm vi</dt><dd>{article.scope}</dd></> : null}
          {article.source_sha256 ? <><dt>SHA-256</dt><dd className="mono">{article.source_sha256}</dd></> : null}
          {article.source_url ? <><dt>Nguồn</dt><dd><a href={article.source_url} target="_blank" rel="noreferrer">Mở PDF gốc <ArrowUpRight size={13} /></a></dd></> : null}
        </dl>
      </>}
      <div className="source-inspect-row">
        <button
          type="button"
          className="button-secondary inspect-pdf-btn"
          onClick={() => {
            const docCode = parseDocCodeFromArticleId(id);
            onInspectPdfChunk?.(docCode, id);
          }}
        >
          <FileSearch size={14} /> Xem file PDF gốc & Chunk
        </button>
      </div>
    </div>}
  </li>;
}

// --------------------------------------------------------------------------- measurements

function Stat({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return <div className="stat"><small>{label}</small><b>{value}</b>{hint && <span>{hint}</span>}</div>;
}

export function Measurements({ run }: { run: RunRecord }) {
  const s = run.snapshot;
  if (!s) return null;
  const u = s.usage;
  const noModel = u?.model_call_count === 0;
  const budget = (b: { used: number; limit: number } | undefined) => (b ? `${b.used} / ${b.limit}` : "—");
  return <section className="panel measurements" aria-label="Số đo của lượt chạy">
    <div className="panel-title"><span>SỐ ĐO CỦA LƯỢT CHẠY</span></div>
    <div className="stats">
      <Stat label="Tổng thời gian" value={formatDuration(s.elapsed_ms)} hint="gồm cả khởi tạo tác tử" />
      <Stat label="Lượt gọi model" value={formatCount(u?.model_call_count)} hint={noModel ? "không gọi model" : `${formatDuration(u?.model_wall_ms)} chờ model`} />
      <Stat label="Token vào / ra" value={noModel ? "—" : `${formatCount(u?.input_tokens)} / ${formatCount(u?.output_tokens)}`} />
      <Stat label="Bước · công cụ · sửa" value={`${budget(s.budgets?.steps)} · ${budget(s.budgets?.tool_calls)} · ${budget(s.budgets?.repairs)}`} hint="đã dùng / giới hạn" />
    </div>
  </section>;
}

export function LexicalPanel({ run }: { run: RunRecord }) {
  const g = run.snapshot?.grounding;
  if (!g) return null;
  const ratio = g.grounded_ratio;
  return <section className="panel lexical" aria-label="Đối soát từ vựng">
    <div className="panel-title"><span><ShieldCheck size={14} /> ĐỐI SOÁT TỪ VỰNG</span><span className="proxy-tag">LEXICAL PROXY</span></div>
    <div className="lexical-row"><b>{ratio == null ? "—" : `${Math.round(ratio * 100)}%`}</b><span>số câu của câu trả lời có đủ trùng từ vựng với mục được trích dẫn. Không phải điểm đúng sai pháp lý hay quy chế.</span></div>
    {g.unsupported_claims.length > 0 && <ul className="unsupported">{g.unsupported_claims.map((c, i) => <li key={i}>{c}</li>)}</ul>}
  </section>;
}
