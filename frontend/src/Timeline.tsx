import {
  Ban, Check, CircleAlert, CircleHelp, FileText, LoaderCircle, Search, ShieldAlert, ShieldCheck, Wrench, X, Layers,
} from "lucide-react";
import { formatCount, formatDuration } from "./format";
import type { Trace, TraceStep } from "./trace";

function ModelLine({ step }: { step: TraceStep }) {
  const m = step.model;
  if (!m) return null;
  return <p className="step-model">Model: {formatDuration(m.wall_ms)} · {formatCount(m.input_tokens)} token vào / {formatCount(m.output_tokens)} token ra{m.action ? ` · chọn "${m.action}"` : ""}</p>;
}

function IdChips({ results, onOpen, disabled }: { results: NonNullable<TraceStep["results"]>; onOpen: (id: string) => void; disabled: boolean }) {
  if (results.length === 0) return <p className="step-note">Không có mục nào được trả về.</p>;
  return <ul className="id-chips">{results.map((r, i) => (
    <li key={`${r.id}-${i}`}><button type="button" disabled={disabled} onClick={() => onOpen(r.id)} title={disabled ? "Mở được khi lượt chạy kết thúc" : "Mở nguyên văn mục này"}><span className="chip-rank">{i + 1}</span><span className="chip-id">{r.id}</span>{r.title && <span className="chip-title">{r.title}</span>}</button></li>
  ))}</ul>;
}

function StepBody({ step, onOpenSource, searchTool, sourcesEnabled, stage1Label }: { step: TraceStep; onOpenSource: (id: string) => void; searchTool?: string; sourcesEnabled: boolean; stage1Label?: string }) {
  switch (step.kind) {
    case "guardrail":
      return <><p className="step-note">Câu hỏi khớp mẫu an ninh của guardrail. Không có lệnh gọi model và không có bước tra cứu.</p></>;
    case "search": {
      const r = step.rerank;
      return <>
        <p className="step-query"><span>truy vấn</span>“{step.query}”</p>
        {r ? <ul className="substeps">
          <li><b>Truy xuất bậc 1</b> {stage1Label || "BM25 + TF-IDF (RRF)"}: {formatCount(r.n_candidates)} ứng viên · {formatDuration(r.first_stage_ms)}</li>
          <li><b>Reranker</b> {r.model ?? r.backend}: chấm {formatCount(r.n_scored)} cặp, giữ {formatCount(step.results?.length)} · {formatDuration(r.wall_ms)}{r.n_truncated ? ` · ${r.n_truncated} cặp bị cắt` : ""}</li>
        </ul> : <p className="step-note">Truy xuất bậc 1 {stage1Label ? `(${stage1Label}, không có reranker)` : "(không có reranker trong cấu hình này)"}.</p>}
        <IdChips results={step.results ?? []} onOpen={onOpenSource} disabled={!sourcesEnabled} />
        <ModelLine step={step} />
      </>;
    }
    case "read":
      return <>
        {step.results && step.results.length > 0
          ? <IdChips results={step.results} onOpen={onOpenSource} disabled={!sourcesEnabled} />
          : <p className="step-note">Không tìm thấy mục “{step.requestedId}” trong corpus.</p>}
        <ModelLine step={step} />
      </>;
    case "verify":
      return <>
        <p className={`verify-line ${step.verifyMode === "off" ? "off" : step.passed ? "pass" : "fail"}`}>
          {step.verifyMode === "off" ? "Kiểm tra tắt (OFF): nhận nguyên văn câu trả lời của model" : step.passed ? "Kiểm tra L1: ĐẠT" : "Kiểm tra L1: KHÔNG ĐẠT"}
        </p>
        <ModelLine step={step} />
      </>;
    case "repair":
      return <>{step.feedback && <p className="step-feedback">{step.feedback}</p>}<p className="step-note">Phản hồi của bộ kiểm tra được đưa lại cho model để sửa.</p></>;
    case "clarify":
      return <><p className="step-note">Model chọn hỏi lại thay vì trả lời.</p><ModelLine step={step} /></>;
    case "refuse":
      return <><p className="step-note">Kết thúc bằng từ chối (không có câu trả lời có căn cứ).</p><ModelLine step={step} /></>;
    case "error":
      return <>
        <p className="step-error">{step.failedTool ? `Bước ${step.failedTool.tool ?? "tra cứu"} thất bại: ${step.failedTool.error_kind ?? "lỗi thành phần"}` : `Lỗi thực thi${step.errorKind ? `: ${step.errorKind}` : ""}`}</p>
        {step.failedTool?.query && <p className="step-query"><span>truy vấn</span>“{step.failedTool.query}”</p>}
        <ModelLine step={step} />
      </>;
    case "running":
      return <p className="step-note">Đang chờ model{searchTool ? ` (công cụ: ${searchTool})` : ""}…</p>;
  }
}

function title(step: TraceStep): { icon: JSX.Element; text: string } {
  switch (step.kind) {
    case "guardrail": return { icon: <ShieldAlert size={16} />, text: "Guardrail chặn đầu vào" };
    case "search": return { icon: <Search size={16} />, text: `Tra cứu${step.tool ? ` · ${step.tool}` : ""}` };
    case "read": return { icon: <FileText size={16} />, text: `Đọc nguyên văn${step.tool ? ` · ${step.tool}` : ""}` };
    case "verify": return { icon: <ShieldCheck size={16} />, text: "Soạn câu trả lời và kiểm tra" };
    case "repair": return { icon: <Wrench size={16} />, text: `Sửa chữa lần ${step.attempt ?? ""}` };
    case "clarify": return { icon: <CircleHelp size={16} />, text: "Hỏi lại người dùng" };
    case "refuse": return { icon: <Ban size={16} />, text: "Từ chối" };
    case "error": return { icon: <CircleAlert size={16} />, text: "Lỗi thực thi" };
    case "running": return { icon: <LoaderCircle size={16} className="spinning" />, text: `Bước ${step.modelStep ?? ""}: model đang xử lý` };
  }
}

export function Timeline({
  trace, nowMs, running, connection, onOpenSource, searchTool, profileLabel, stage1Label,
}: {
  trace: Trace; nowMs: number | null; running: boolean; connection: string; onOpenSource: (id: string) => void; searchTool?: string; profileLabel?: string; stage1Label?: string;
}) {
  const total = trace.totalMs ?? (running ? nowMs : null);
  return <section className="timeline-card" aria-label="Quy trình xử lý">
    <div className="timeline-head">
      <div><span className="kicker">QUY TRÌNH XỬ LÝ</span><h2>Các bước của tác tử</h2></div>
      <div className="timeline-total" aria-label="Tổng thời gian"><b>{formatDuration(total)}</b><small>{trace.finished ? "tổng" : running ? "đang chạy" : ""}</small></div>
    </div>
    {profileLabel && <p className="timeline-profile">{profileLabel}</p>}
    {trace.steps.length === 0 ? <div className="timeline-empty">{running ? <><LoaderCircle size={18} className="spinning" /> Chờ sự kiện đầu tiên từ worker…</> : connection === "disconnected" ? "Mất kết nối sự kiện." : "Chưa có bản ghi sự kiện cho lượt chạy này."}</div> :
      <ol className="steps">
        {trace.queueMs !== null && trace.queueMs >= 500 && <li className="step step-queue"><span className="step-dot"><Layers size={14} /></span><div className="step-main"><div className="step-line"><b>Chờ hàng đợi</b><span className="step-time">{formatDuration(trace.queueMs)}</span></div></div></li>}
        {trace.steps.map((step, index) => {
          const t = title(step);
          const live = step.kind === "running";
          const dur = live ? (nowMs !== null ? Math.max(0, nowMs - step.startMs) : null) : step.durationMs;
          const bad = step.kind === "error" || (step.kind === "verify" && step.verifyMode !== "off" && !step.passed) || step.kind === "guardrail";
          return <li key={step.key} className={`step step-${step.kind} ${bad ? "step-bad" : ""}`}>
            <span className="step-dot">{t.icon}</span>
            <div className="step-main">
              <div className="step-line"><b><span className="step-index">{index + 1}</span>{t.text}</b>{dur !== null && !(step.kind === "repair") && <span className="step-time" title={`bắt đầu +${formatDuration(step.startMs)}`}>{formatDuration(dur)}</span>}</div>
              <StepBody step={step} onOpenSource={onOpenSource} searchTool={searchTool} sourcesEnabled={!running} stage1Label={stage1Label} />
            </div>
          </li>;
        })}
        {trace.finished && <li className="step step-end"><span className="step-dot">{trace.steps.some((s) => s.kind === "error") ? <X size={14} /> : <Check size={14} />}</span><div className="step-main"><div className="step-line"><b>Kết thúc</b><span className="step-time">{formatDuration(trace.totalMs)}</span></div></div></li>}
      </ol>}
    <p className="timeline-privacy"><ShieldCheck size={14} /> Chỉ hiển thị sự kiện vận hành và số đo thực; không hiển thị suy luận của model.</p>
  </section>;
}
