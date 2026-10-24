#!/usr/bin/env python3
"""Interactive Web Platform for D2 Blind Human Audit of the LLM Judge.

Reads:
  - evaluation/runs/d2-gpu-r2-4b-hcmut-v1/analysis/human-audit/{packets.json,labels.csv}
  - evaluation/runs/d2-gpu-r2-4b-labour-v1/analysis/human-audit/{packets.json,labels.csv}

Writes (only when the human reviewer saves/submits labels in the UI):
  - labels.csv in each run's human-audit directory
  - agreement.json and agreement.md via evaluation/score_benchmark_audit.py
"""
from __future__ import annotations

import csv
import json
import re
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import parse_qs, urlparse

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from evaluation import score_benchmark_audit

RUNS: Dict[str, Path] = {
    "hcmut": REPO_ROOT / "evaluation/runs/d2-gpu-r2-4b-hcmut-v1",
    "labour": REPO_ROOT / "evaluation/runs/d2-gpu-r2-4b-labour-v1",
}

LABEL_COLUMNS = [
    "review_id",
    "reviewer",
    "judgeable",
    "behaviour_appropriate",
    "correctness",
    "completeness",
    "total_claims",
    "unsupported_claims",
    "notes",
]

REFUSAL_PATTERNS = re.compile(
    r"(không có thông tin|ngoài phạm vi|chưa có quy định|từ chối trả lời|không tìm thấy thông tin|"
    r"không đủ căn cứ|không nằm trong cơ sở dữ liệu|liên hệ đơn vị|liên hệ cơ quan)",
    re.IGNORECASE,
)


def estimate_factual_sentences(candidate_behavior: str, candidate_answer: str) -> int:
    """Helper count of non-abstention sentences in candidate_answer for UI convenience."""
    if candidate_behavior in ("refused", "clarification"):
        return 0
    text = (candidate_answer or "").strip()
    if not text:
        return 0
    lines = [ln.strip() for ln in re.split(r"[\n]+", text) if ln.strip()]
    claims = 0
    for ln in lines:
        cleaned = re.sub(r"^[-*•\d.)+\s]+", "", ln).strip()
        if not cleaned or cleaned.endswith(":"):
            continue
        if REFUSAL_PATTERNS.search(cleaned) and len(lines) == 1:
            continue
        claims += 1
    return max(1, claims) if claims == 0 else claims


def load_benchmark_data(bm_key: str) -> Dict[str, Any]:
    run_dir = RUNS[bm_key]
    audit_dir = run_dir / "analysis" / "human-audit"
    packets: List[Dict[str, Any]] = json.loads((audit_dir / "packets.json").read_text(encoding="utf-8"))
    labels_by_id: Dict[str, Dict[str, str]] = {}
    csv_path = audit_dir / "labels.csv"
    if csv_path.is_file():
        with csv_path.open("r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rid = (row.get("review_id") or "").strip()
                if rid:
                    labels_by_id[rid] = {col: (row.get(col) or "").strip() for col in LABEL_COLUMNS}

    enriched = []
    for idx, p in enumerate(packets):
        rid = p["review_id"]
        lbl = labels_by_id.get(rid, {col: "" for col in LABEL_COLUMNS})
        is_labelled = any(
            lbl.get(k, "") != ""
            for k in ("judgeable", "behaviour_appropriate", "correctness", "completeness", "total_claims", "unsupported_claims")
        )
        # Check quote presence in source_articles for visual aid
        all_source_text = "\n".join((a.get("content") or "") for a in p.get("source_articles", []))
        norm_source = re.sub(r"\s+", " ", all_source_text).lower()
        cit_checks = []
        for cit in p.get("candidate_citations", []):
            q = (cit.get("exact_quote") or "").strip()
            norm_q = re.sub(r"\s+", " ", q).lower()
            found = bool(norm_q and norm_q in norm_source)
            cit_checks.append({
                "article_id": cit.get("article_id", ""),
                "exact_quote": q,
                "verbatim_in_source": found,
            })
        enriched.append({
            **p,
            "index": idx + 1,
            "label": lbl,
            "is_labelled": is_labelled,
            "suggested_claims_count": estimate_factual_sentences(p.get("candidate_behavior", ""), p.get("candidate_answer", "")),
            "citation_checks": cit_checks,
        })

    agreement = None
    ag_path = audit_dir / "agreement.json"
    if ag_path.is_file():
        try:
            agreement = json.loads(ag_path.read_text(encoding="utf-8"))
        except Exception:
            agreement = None

    return {
        "benchmark": bm_key,
        "run_id": run_dir.name,
        "total": len(enriched),
        "labelled_count": sum(1 for item in enriched if item["is_labelled"]),
        "items": enriched,
        "agreement": agreement,
    }


def save_label_row(bm_key: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    run_dir = RUNS[bm_key]
    audit_dir = run_dir / "analysis" / "human-audit"
    packets: List[Dict[str, Any]] = json.loads((audit_dir / "packets.json").read_text(encoding="utf-8"))
    sample_ids = [p["review_id"] for p in packets]
    target_rid = str(payload.get("review_id") or "").strip()
    if target_rid not in sample_ids:
        raise ValueError(f"Unknown review_id: {target_rid}")

    csv_path = audit_dir / "labels.csv"
    existing: Dict[str, Dict[str, str]] = {}
    if csv_path.is_file():
        with csv_path.open("r", newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                rid = (row.get("review_id") or "").strip()
                if rid:
                    existing[rid] = {col: (row.get(col) or "").strip() for col in LABEL_COLUMNS}

    if payload.get("clear"):
        existing[target_rid] = {col: (target_rid if col == "review_id" else "") for col in LABEL_COLUMNS}
    else:
        existing[target_rid] = {
            "review_id": target_rid,
            "reviewer": str(payload.get("reviewer") or "Võ Phạm Tuấn Dũng").strip(),
            "judgeable": str(payload.get("judgeable", "1")).strip(),
            "behaviour_appropriate": str(payload.get("behaviour_appropriate", "")).strip(),
            "correctness": str(payload.get("correctness", "")).strip(),
            "completeness": str(payload.get("completeness", "")).strip(),
            "total_claims": str(payload.get("total_claims", "")).strip(),
            "unsupported_claims": str(payload.get("unsupported_claims", "")).strip(),
            "notes": str(payload.get("notes", "")).strip(),
        }

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=LABEL_COLUMNS)
        writer.writeheader()
        for rid in sample_ids:
            row = existing.get(rid) or {col: (rid if col == "review_id" else "") for col in LABEL_COLUMNS}
            writer.writerow(row)

    # Also run scorer if >= 10 items are labelled
    labelled_now = sum(
        1
        for rid in sample_ids
        if any(existing.get(rid, {}).get(k, "") != "" for k in LABEL_COLUMNS[2:8])
    )
    score_res = None
    if labelled_now >= 10:
        score_res = score_benchmark_audit.score(run_dir, [csv_path], min_items=10)
        if score_res.get("status") == "ok":
            (audit_dir / "agreement.json").write_text(
                json.dumps(score_res, ensure_ascii=False, indent=2, default=str) + "\n",
                encoding="utf-8",
            )
            (audit_dir / "agreement.md").write_text(
                score_benchmark_audit.to_markdown(score_res),
                encoding="utf-8",
            )
    return {
        "ok": True,
        "labelled_count": labelled_now,
        "total": len(sample_ids),
        "agreement": score_res,
    }


def run_scorer_all() -> Dict[str, Any]:
    results = {}
    for bm_key, run_dir in RUNS.items():
        audit_dir = run_dir / "analysis" / "human-audit"
        csv_path = audit_dir / "labels.csv"
        res = score_benchmark_audit.score(run_dir, [csv_path], min_items=10)
        (audit_dir / "agreement.json").write_text(
            json.dumps(res, ensure_ascii=False, indent=2, default=str) + "\n",
            encoding="utf-8",
        )
        (audit_dir / "agreement.md").write_text(
            score_benchmark_audit.to_markdown(res),
            encoding="utf-8",
        )
        results[bm_key] = res
    return results


INDEX_HTML = r"""<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>LuatCheck D2 — Blind Human Audit Platform</title>
<style>
  :root {
    --bg: #0f172a;
    --panel: #1e293b;
    --panel-alt: #273549;
    --border: #334155;
    --text: #f8fafc;
    --muted: #94a3b8;
    --primary: #3b82f6;
    --primary-hover: #2563eb;
    --success: #10b981;
    --warn: #f59e0b;
    --danger: #ef4444;
    --gold-bg: rgba(245, 158, 11, 0.22);
    --cand-bg: rgba(16, 185, 129, 0.22);
  }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background: var(--bg);
    color: var(--text);
    height: 100vh;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }
  header {
    background: var(--panel);
    border-bottom: 1px solid var(--border);
    padding: 10px 18px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 14px;
    flex-shrink: 0;
  }
  .brand {
    display: flex;
    align-items: center;
    gap: 12px;
  }
  .brand h1 {
    font-size: 16px;
    margin: 0;
    font-weight: 700;
  }
  .tabs {
    display: flex;
    gap: 8px;
  }
  .tab-btn {
    background: var(--panel-alt);
    color: var(--text);
    border: 1px solid var(--border);
    padding: 7px 14px;
    border-radius: 6px;
    cursor: pointer;
    font-weight: 600;
    font-size: 13px;
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .tab-btn.active {
    background: var(--primary);
    border-color: var(--primary);
  }
  .badge {
    font-size: 11px;
    padding: 2px 7px;
    border-radius: 99px;
    background: rgba(255,255,255,0.15);
  }
  .header-right {
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 13px;
  }
  .reviewer-input {
    background: var(--bg);
    color: var(--text);
    border: 1px solid var(--border);
    padding: 5px 10px;
    border-radius: 5px;
    font-size: 13px;
    width: 175px;
  }
  .score-btn {
    background: var(--success);
    color: #052e16;
    font-weight: 700;
    border: none;
    padding: 7px 14px;
    border-radius: 6px;
    cursor: pointer;
    font-size: 13px;
  }
  .score-btn:hover { opacity: 0.92; }

  /* Item strip */
  .item-strip {
    background: #162032;
    border-bottom: 1px solid var(--border);
    padding: 8px 18px;
    display: flex;
    align-items: center;
    gap: 6px;
    overflow-x: auto;
    flex-shrink: 0;
  }
  .pill-idx {
    min-width: 30px;
    height: 26px;
    border-radius: 5px;
    border: 1px solid var(--border);
    background: var(--panel);
    color: var(--muted);
    font-size: 12px;
    font-weight: 600;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    justify-content: center;
  }
  .pill-idx.done {
    background: rgba(16, 185, 129, 0.18);
    border-color: var(--success);
    color: #6ee7b7;
  }
  .pill-idx.current {
    outline: 2px solid #60a5fa;
    color: #fff;
  }

  /* Main layout */
  .workspace {
    flex: 1;
    display: grid;
    grid-template-columns: 1.05fr 0.95fr;
    gap: 0;
    overflow: hidden;
  }
  .pane {
    padding: 16px 20px;
    overflow-y: auto;
    height: 100%;
  }
  .pane-left {
    border-right: 1px solid var(--border);
  }
  .card {
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 14px 16px;
    margin-bottom: 14px;
  }
  .card-title {
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--muted);
    margin: 0 0 8px 0;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  .q-text {
    font-size: 15px;
    font-weight: 600;
    line-height: 1.5;
  }
  .beh-row {
    display: flex;
    gap: 10px;
    margin-top: 10px;
    flex-wrap: wrap;
  }
  .beh-tag {
    font-size: 12px;
    font-weight: 700;
    padding: 4px 10px;
    border-radius: 5px;
  }
  .beh-match { background: rgba(16, 185, 129, 0.2); color: #6ee7b7; border: 1px solid #059669; }
  .beh-mismatch { background: rgba(239, 68, 68, 0.2); color: #fca5a5; border: 1px solid #dc2626; }
  .beh-neutral { background: var(--panel-alt); color: var(--text); border: 1px solid var(--border); }

  .ans-box {
    white-space: pre-wrap;
    line-height: 1.55;
    font-size: 14px;
    background: rgba(15, 23, 42, 0.55);
    padding: 10px 12px;
    border-radius: 6px;
    border: 1px solid var(--border);
  }
  .quote-list {
    margin: 8px 0 0 0;
    padding: 0;
    list-style: none;
    display: flex;
    flex-direction: column;
    gap: 6px;
  }
  .quote-item {
    font-size: 13px;
    padding: 7px 10px;
    border-radius: 5px;
    background: var(--panel-alt);
    border-left: 3px solid var(--primary);
    line-height: 1.45;
  }
  .quote-item.gold { border-left-color: var(--warn); }
  .quote-item.cand-ok { border-left-color: var(--success); }
  .quote-item.cand-miss { border-left-color: var(--danger); }

  .article-box {
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 14px 16px;
    margin-bottom: 14px;
  }
  .article-header {
    font-weight: 700;
    font-size: 14px;
    color: #93c5fd;
    margin-bottom: 4px;
  }
  .article-sub {
    font-size: 12px;
    color: var(--muted);
    margin-bottom: 10px;
  }
  .article-content {
    white-space: pre-wrap;
    font-size: 13.5px;
    line-height: 1.6;
    background: rgba(15, 23, 42, 0.6);
    padding: 12px;
    border-radius: 6px;
    max-height: 440px;
    overflow-y: auto;
  }
  mark.hl-gold {
    background: var(--gold-bg);
    color: #fde68a;
    padding: 1px 3px;
    border-radius: 3px;
    border-bottom: 1px dashed var(--warn);
  }
  mark.hl-cand {
    background: var(--cand-bg);
    color: #a7f3d0;
    padding: 1px 3px;
    border-radius: 3px;
    border-bottom: 1px solid var(--success);
  }

  /* Sticky Grading Panel */
  .grade-panel {
    background: #17253b;
    border: 2px solid #3b82f6;
    border-radius: 10px;
    padding: 14px 16px;
    margin-bottom: 16px;
  }
  .presets-bar {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 8px;
    margin-bottom: 12px;
  }
  .preset-btn {
    padding: 9px 10px;
    border-radius: 6px;
    border: 1px solid var(--border);
    font-weight: 600;
    font-size: 12.5px;
    cursor: pointer;
    text-align: left;
    display: flex;
    align-items: center;
    justify-content: space-between;
  }
  .preset-pass { background: rgba(16, 185, 129, 0.2); color: #a7f3d0; border-color: #059669; }
  .preset-pass:hover { background: rgba(16, 185, 129, 0.32); }
  .preset-refuse { background: rgba(59, 130, 246, 0.2); color: #bfdbfe; border-color: #2563eb; }
  .preset-refuse:hover { background: rgba(59, 130, 246, 0.32); }
  .preset-overref { background: rgba(239, 68, 68, 0.2); color: #fecaca; border-color: #dc2626; }
  .preset-overref:hover { background: rgba(239, 68, 68, 0.32); }
  .preset-partial { background: rgba(245, 158, 11, 0.2); color: #fde68a; border-color: #d97706; }
  .preset-partial:hover { background: rgba(245, 158, 11, 0.32); }
  .kbd {
    font-family: monospace;
    font-size: 11px;
    background: rgba(0,0,0,0.35);
    padding: 2px 6px;
    border-radius: 4px;
  }

  .form-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 10px;
    margin-bottom: 10px;
  }
  .field-box {
    background: rgba(15, 23, 42, 0.65);
    border: 1px solid var(--border);
    padding: 8px 10px;
    border-radius: 6px;
  }
  .field-box label {
    display: block;
    font-size: 11px;
    color: var(--muted);
    margin-bottom: 6px;
    font-weight: 600;
  }
  .seg-group {
    display: flex;
    gap: 4px;
  }
  .seg-btn {
    flex: 1;
    padding: 5px 0;
    background: var(--panel);
    color: var(--muted);
    border: 1px solid var(--border);
    border-radius: 4px;
    font-size: 12px;
    font-weight: 700;
    cursor: pointer;
  }
  .seg-btn.active {
    background: var(--primary);
    color: #fff;
    border-color: var(--primary);
  }
  .num-input {
    width: 100%;
    background: var(--panel);
    color: var(--text);
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: 5px 8px;
    font-size: 13px;
    font-weight: 700;
  }
  .notes-row {
    display: flex;
    gap: 8px;
    margin-top: 8px;
  }
  .notes-input {
    flex: 1;
    background: var(--bg);
    color: var(--text);
    border: 1px solid var(--border);
    border-radius: 5px;
    padding: 7px 10px;
    font-size: 13px;
  }
  .action-bar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: 12px;
    gap: 8px;
  }
  .btn {
    padding: 8px 14px;
    border-radius: 6px;
    border: 1px solid var(--border);
    background: var(--panel-alt);
    color: var(--text);
    font-weight: 600;
    font-size: 13px;
    cursor: pointer;
  }
  .btn-save {
    background: var(--primary);
    border-color: var(--primary);
    color: #fff;
    flex: 1;
  }
  .btn-save:hover { background: var(--primary-hover); }

  /* Modal */
  .modal-backdrop {
    position: fixed;
    inset: 0;
    background: rgba(0,0,0,0.7);
    display: none;
    align-items: center;
    justify-content: center;
    z-index: 100;
  }
  .modal {
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 10px;
    width: min(760px, 92vw);
    max-height: 85vh;
    overflow-y: auto;
    padding: 20px;
  }
  table.res-table {
    width: 100%;
    border-collapse: collapse;
    margin-top: 10px;
    font-size: 13px;
  }
  table.res-table th, table.res-table td {
    border: 1px solid var(--border);
    padding: 7px 10px;
    text-align: left;
  }
  table.res-table th { background: var(--panel-alt); }
</style>
</head>
<body>

<header>
  <div class="brand">
    <h1>⚖️ LuatCheck D2 — Blind Human Audit</h1>
    <div class="tabs">
      <button class="tab-btn active" id="tab-hcmut" onclick="switchBenchmark('hcmut')">
        HCMUT Regulations <span class="badge" id="badge-hcmut">0/30</span>
      </button>
      <button class="tab-btn" id="tab-labour" onclick="switchBenchmark('labour')">
        Labour Law <span class="badge" id="badge-labour">0/30</span>
      </button>
    </div>
  </div>
  <div class="header-right">
    <label for="reviewer-name" style="color:var(--muted)">Reviewer:</label>
    <input id="reviewer-name" class="reviewer-input" value="Võ Phạm Tuấn Dũng" />
    <button class="btn" onclick="jumpNextUnlabelled()" title="Jump to next unlabelled item">⏭ Next Unlabelled</button>
    <button class="score-btn" onclick="computeAllAgreement()">📊 Compute Agreement & κ</button>
  </div>
</header>

<div class="item-strip" id="item-strip"></div>

<div class="workspace">
  <!-- LEFT PANE: Question, Reference, Candidate, and Grading Form -->
  <div class="pane pane-left">
    <!-- Grading Panel at Top-Left for Fast Workflow -->
    <div class="grade-panel">
      <div class="card-title">
        <span>📝 Human Verdict — Item <span id="lbl-idx">#1</span> (<code id="lbl-rid"></code>)</span>
        <span id="lbl-status" style="font-weight:700"></span>
      </div>

      <div class="presets-bar">
        <button class="preset-btn preset-pass" onclick="applyPreset('perfect_answer')">
          <span>✅ Answer Đúng & Đủ (2/2, 0 unsupp)</span>
          <span class="kbd">Key 1</span>
        </button>
        <button class="preset-btn preset-refuse" onclick="applyPreset('valid_refusal')">
          <span>🛡️ Refuse Đúng (Out-of-scope, 0 claim)</span>
          <span class="kbd">Key 2</span>
        </button>
        <button class="preset-btn preset-overref" onclick="applyPreset('over_refusal')">
          <span>❌ Over-Refusal (Từ chối câu có đáp án)</span>
          <span class="kbd">Key 3</span>
        </button>
        <button class="preset-btn preset-partial" onclick="applyPreset('partial_answer')">
          <span>⚠️ Đúng 1 phần / Thiếu ý (1/1)</span>
          <span class="kbd">Key 4</span>
        </button>
      </div>

      <div class="form-grid">
        <div class="field-box">
          <label>1. Judgeable</label>
          <div class="seg-group" id="seg-judgeable">
            <button class="seg-btn" onclick="setField('judgeable','1')">1 (Yes)</button>
            <button class="seg-btn" onclick="setField('judgeable','0')">0 (No)</button>
          </div>
        </div>
        <div class="field-box">
          <label>2. Behaviour Appropriate</label>
          <div class="seg-group" id="seg-behaviour">
            <button class="seg-btn" onclick="setField('behaviour_appropriate','1')">1 (Match)</button>
            <button class="seg-btn" onclick="setField('behaviour_appropriate','0')">0 (Wrong)</button>
          </div>
        </div>
        <div class="field-box">
          <label>3. Correctness (0–2)</label>
          <div class="seg-group" id="seg-correctness">
            <button class="seg-btn" onclick="setField('correctness','0')">0</button>
            <button class="seg-btn" onclick="setField('correctness','1')">1</button>
            <button class="seg-btn" onclick="setField('correctness','2')">2</button>
          </div>
        </div>
        <div class="field-box">
          <label>4. Completeness (0–2)</label>
          <div class="seg-group" id="seg-completeness">
            <button class="seg-btn" onclick="setField('completeness','0')">0</button>
            <button class="seg-btn" onclick="setField('completeness','1')">1</button>
            <button class="seg-btn" onclick="setField('completeness','2')">2</button>
          </div>
        </div>
        <div class="field-box">
          <label>5. Total Claims <span id="hint-claims" style="color:#60a5fa"></span></label>
          <input type="number" min="0" id="inp-total-claims" class="num-input" value="1" />
        </div>
        <div class="field-box">
          <label>6. Unsupported Claims</label>
          <input type="number" min="0" id="inp-unsupp-claims" class="num-input" value="0" />
        </div>
      </div>

      <div class="notes-row">
        <input type="text" id="inp-notes" class="notes-input" placeholder="Ghi chú tùy chọn (notes)..." />
      </div>

      <div class="action-bar">
        <button class="btn" onclick="prevItem()">⬅ Prev ( [ )</button>
        <button class="btn" onclick="clearCurrentItem()" style="color:#fca5a5">Clear</button>
        <button class="btn btn-save" onclick="saveCurrentItem(true)">💾 Save & Next (Enter / ] )</button>
      </div>
    </div>

    <!-- Question & Behaviour -->
    <div class="card">
      <div class="card-title"><span>❓ Question & Expected Behaviour</span></div>
      <div class="q-text" id="q-text"></div>
      <div class="beh-row" id="beh-row"></div>
    </div>

    <!-- Candidate Output -->
    <div class="card">
      <div class="card-title">
        <span>🤖 Candidate Output (Blind Trial)</span>
        <span id="cand-cit-summary"></span>
      </div>
      <div class="ans-box" id="cand-answer"></div>
      <ul class="quote-list" id="cand-quotes"></ul>
    </div>

    <!-- Gold Reference -->
    <div class="card">
      <div class="card-title"><span>🎯 Gold Reference Answer & Verbatim Quotes</span></div>
      <div class="ans-box" id="ref-answer" style="border-color: rgba(245, 158, 11, 0.4)"></div>
      <ul class="quote-list" id="ref-quotes"></ul>
    </div>
  </div>

  <!-- RIGHT PANE: Full Source Articles with Quote Highlighting -->
  <div class="pane">
    <div class="card-title" style="margin-bottom:10px">
      <span>📚 Source Articles (Gold = <mark class="hl-gold">Vàng</mark>, Candidate Citation = <mark class="hl-cand">Xanh lá</mark>)</span>
    </div>
    <div id="source-articles"></div>
  </div>
</div>

<!-- Agreement Modal -->
<div class="modal-backdrop" id="modal-backdrop" onclick="if(event.target===this)this.style.display='none'">
  <div class="modal">
    <div style="display:flex;justify-content:space-between;align-items:center">
      <h2 style="margin:0;font-size:18px">📊 Judge vs Human Agreement Summary</h2>
      <button class="btn" onclick="document.getElementById('modal-backdrop').style.display='none'">Đóng</button>
    </div>
    <div id="modal-body" style="margin-top:12px"></div>
  </div>
</div>

<script>
let STATE = {
  bm: 'hcmut',
  data: { hcmut: null, labour: null },
  idx: 0,
  form: {
    judgeable: '1',
    behaviour_appropriate: '1',
    correctness: '2',
    completeness: '2',
  }
};

async function fetchAll() {
  const [hRes, lRes] = await Promise.all([
    fetch('/api/data?bm=hcmut').then(r => r.json()),
    fetch('/api/data?bm=labour').then(r => r.json())
  ]);
  STATE.data.hcmut = hRes;
  STATE.data.labour = lRes;
  updateBadges();
  renderCurrent();
}

function updateBadges() {
  for (const k of ['hcmut', 'labour']) {
    const d = STATE.data[k];
    if (d) {
      document.getElementById(`badge-${k}`).textContent = `${d.labelled_count}/${d.total}`;
    }
  }
}

function switchBenchmark(bm) {
  STATE.bm = bm;
  STATE.idx = 0;
  document.getElementById('tab-hcmut').classList.toggle('active', bm === 'hcmut');
  document.getElementById('tab-labour').classList.toggle('active', bm === 'labour');
  renderCurrent();
}

function currentItem() {
  const d = STATE.data[STATE.bm];
  return d ? d.items[STATE.idx] : null;
}

function setField(field, val) {
  STATE.form[field] = String(val);
  syncSegmentUI();
}

function syncSegmentUI() {
  const map = {
    'judgeable': 'seg-judgeable',
    'behaviour_appropriate': 'seg-behaviour',
    'correctness': 'seg-correctness',
    'completeness': 'seg-completeness'
  };
  for (const [field, elId] of Object.entries(map)) {
    const container = document.getElementById(elId);
    const val = STATE.form[field];
    Array.from(container.querySelectorAll('.seg-btn')).forEach(btn => {
      const btnVal = btn.textContent.trim().charAt(0);
      btn.classList.toggle('active', btnVal === String(val));
    });
  }
}

function escapeHtml(s) {
  return String(s || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

function highlightSourceContent(rawText, goldQuotes, candQuotes) {
  let html = escapeHtml(rawText);
  const highlightList = [
    ...candQuotes.map(q => ({ q: q.exact_quote, cls: 'hl-cand' })),
    ...goldQuotes.map(q => ({ q: q.exact_quote, cls: 'hl-gold' }))
  ].filter(x => x.q && x.q.trim().length >= 6);

  for (const { q, cls } of highlightList) {
    const escapedQ = escapeHtml(q.trim());
    const flexPattern = escapedQ
      .replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
      .replace(/\s+/g, '\\s+');
    try {
      const re = new RegExp(`(${flexPattern})`, 'gi');
      html = html.replace(re, `<mark class="${cls}">$1</mark>`);
    } catch (e) {}
  }
  return html;
}

function renderCurrent() {
  const d = STATE.data[STATE.bm];
  if (!d) return;
  const strip = document.getElementById('item-strip');
  strip.innerHTML = '';
  d.items.forEach((it, i) => {
    const b = document.createElement('button');
    b.className = 'pill-idx' + (it.is_labelled ? ' done' : '') + (i === STATE.idx ? ' current' : '');
    b.textContent = i + 1;
    b.onclick = () => { STATE.idx = i; renderCurrent(); };
    strip.appendChild(b);
  });

  const item = currentItem();
  if (!item) return;

  document.getElementById('lbl-idx').textContent = `#${item.index} / ${d.total}`;
  document.getElementById('lbl-rid').textContent = item.review_id;
  const st = document.getElementById('lbl-status');
  if (item.is_labelled) {
    st.textContent = '✓ ĐÃ CHẤM';
    st.style.color = '#10b981';
  } else {
    st.textContent = '• CHƯA CHẤM';
    st.style.color = '#f59e0b';
  }

  // Question & Behaviour
  document.getElementById('q-text').textContent = item.question;
  const exp = item.expected_behavior;
  const cand = item.candidate_behavior;
  const behMatch = (exp === 'answer' && cand === 'answered') || (exp === 'refuse' && cand === 'refused');
  const behRow = document.getElementById('beh-row');
  behRow.innerHTML = `
    <span class="beh-tag beh-neutral">Expected: ${exp.toUpperCase()}</span>
    <span class="beh-tag ${behMatch ? 'beh-match' : 'beh-mismatch'}">Candidate: ${cand.toUpperCase()} (${behMatch ? 'MATCH' : 'MISMATCH'})</span>
  `;

  // Candidate Answer & Quotes
  document.getElementById('cand-answer').textContent = item.candidate_answer || '(Trống)';
  const candQuotesEl = document.getElementById('cand-quotes');
  candQuotesEl.innerHTML = '';
  (item.citation_checks || []).forEach(c => {
    const li = document.createElement('li');
    li.className = 'quote-item ' + (c.verbatim_in_source ? 'cand-ok' : 'cand-miss');
    li.innerHTML = `<strong>[${escapeHtml(c.article_id)}]</strong> ${c.verbatim_in_source ? '✅ Khớp nguyên văn' : '⚠️ Trích dẫn rút gọn/không khớp 100%'}: “${escapeHtml(c.exact_quote)}”`;
    candQuotesEl.appendChild(li);
  });
  document.getElementById('cand-cit-summary').textContent = `${(item.citation_checks || []).length} trích dẫn`;

  // Reference Answer & Quotes
  document.getElementById('ref-answer').textContent = item.reference_answer || '(Câu hỏi ngoài phạm vi — cần từ chối)';
  const refQuotesEl = document.getElementById('ref-quotes');
  refQuotesEl.innerHTML = '';
  (item.reference_evidence || []).forEach(r => {
    const li = document.createElement('li');
    li.className = 'quote-item gold';
    li.innerHTML = `<strong>[${escapeHtml(r.article_id)}]</strong> “${escapeHtml(r.exact_quote)}”`;
    refQuotesEl.appendChild(li);
  });

  // Source Articles
  const srcContainer = document.getElementById('source-articles');
  srcContainer.innerHTML = '';
  (item.source_articles || []).forEach(art => {
    const box = document.createElement('div');
    box.className = 'article-box';
    const hlContent = highlightSourceContent(art.content || '', item.reference_evidence || [], item.candidate_citations || []);
    box.innerHTML = `
      <div class="article-header">${escapeHtml(art.article_id)} — ${escapeHtml(art.title)}</div>
      <div class="article-sub">${escapeHtml(art.source_name)}</div>
      <div class="article-content">${hlContent}</div>
    `;
    srcContainer.appendChild(box);
  });

  // Populate Form from saved label or smart defaults
  const lbl = item.label || {};
  document.getElementById('hint-claims').textContent = `(gợi ý: ${item.suggested_claims_count})`;
  if (item.is_labelled) {
    STATE.form.judgeable = lbl.judgeable !== '' ? lbl.judgeable : '1';
    STATE.form.behaviour_appropriate = lbl.behaviour_appropriate !== '' ? lbl.behaviour_appropriate : (behMatch ? '1' : '0');
    STATE.form.correctness = lbl.correctness !== '' ? lbl.correctness : '2';
    STATE.form.completeness = lbl.completeness !== '' ? lbl.completeness : '2';
    document.getElementById('inp-total-claims').value = lbl.total_claims !== '' ? lbl.total_claims : item.suggested_claims_count;
    document.getElementById('inp-unsupp-claims').value = lbl.unsupported_claims !== '' ? lbl.unsupported_claims : '0';
    document.getElementById('inp-notes').value = lbl.notes || '';
  } else {
    // Smart pre-fill based on expected vs candidate behavior (reviewer still inspects and clicks Save)
    STATE.form.judgeable = '1';
    STATE.form.behaviour_appropriate = behMatch ? '1' : '0';
    if (!behMatch && cand !== 'answered') {
      // Over-refusal or clarification when answer expected
      STATE.form.correctness = '0';
      STATE.form.completeness = '0';
      document.getElementById('inp-total-claims').value = 0;
      document.getElementById('inp-unsupp-claims').value = 0;
    } else if (exp === 'refuse' && cand === 'refused') {
      STATE.form.correctness = '2';
      STATE.form.completeness = '2';
      document.getElementById('inp-total-claims').value = 0;
      document.getElementById('inp-unsupp-claims').value = 0;
    } else {
      STATE.form.correctness = '2';
      STATE.form.completeness = '2';
      document.getElementById('inp-total-claims').value = item.suggested_claims_count;
      document.getElementById('inp-unsupp-claims').value = 0;
    }
    document.getElementById('inp-notes').value = '';
  }
  syncSegmentUI();
}

function applyPreset(kind) {
  const item = currentItem();
  if (!item) return;
  STATE.form.judgeable = '1';
  if (kind === 'perfect_answer') {
    STATE.form.behaviour_appropriate = '1';
    STATE.form.correctness = '2';
    STATE.form.completeness = '2';
    document.getElementById('inp-total-claims').value = Math.max(1, item.suggested_claims_count);
    document.getElementById('inp-unsupp-claims').value = 0;
  } else if (kind === 'valid_refusal') {
    STATE.form.behaviour_appropriate = '1';
    STATE.form.correctness = '2';
    STATE.form.completeness = '2';
    document.getElementById('inp-total-claims').value = 0;
    document.getElementById('inp-unsupp-claims').value = 0;
  } else if (kind === 'over_refusal') {
    STATE.form.behaviour_appropriate = '0';
    STATE.form.correctness = '0';
    STATE.form.completeness = '0';
    document.getElementById('inp-total-claims').value = 0;
    document.getElementById('inp-unsupp-claims').value = 0;
  } else if (kind === 'partial_answer') {
    STATE.form.behaviour_appropriate = '1';
    STATE.form.correctness = '1';
    STATE.form.completeness = '1';
    document.getElementById('inp-total-claims').value = Math.max(1, item.suggested_claims_count);
    document.getElementById('inp-unsupp-claims').value = 0;
  }
  syncSegmentUI();
  saveCurrentItem(true);
}

async function saveCurrentItem(advance) {
  const item = currentItem();
  if (!item) return;
  const reviewer = document.getElementById('reviewer-name').value.trim() || 'Võ Phạm Tuấn Dũng';
  const totalClaims = parseInt(document.getElementById('inp-total-claims').value || '0', 10);
  const unsuppClaims = parseInt(document.getElementById('inp-unsupp-claims').value || '0', 10);
  if (unsuppClaims > totalClaims) {
    alert('Unsupported claims không được lớn hơn Total claims!');
    return;
  }
  const payload = {
    bm: STATE.bm,
    review_id: item.review_id,
    reviewer: reviewer,
    judgeable: STATE.form.judgeable,
    behaviour_appropriate: STATE.form.behaviour_appropriate,
    correctness: STATE.form.correctness,
    completeness: STATE.form.completeness,
    total_claims: String(totalClaims),
    unsupported_claims: String(unsuppClaims),
    notes: document.getElementById('inp-notes').value.trim()
  };
  const res = await fetch('/api/save', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  }).then(r => r.json());

  if (res.ok) {
    item.label = payload;
    item.is_labelled = true;
    STATE.data[STATE.bm].labelled_count = res.labelled_count;
    updateBadges();
    if (advance && STATE.idx < STATE.data[STATE.bm].items.length - 1) {
      STATE.idx += 1;
    }
    renderCurrent();
  } else {
    alert('Lỗi khi lưu: ' + (res.error || 'Unknown'));
  }
}

async function clearCurrentItem() {
  const item = currentItem();
  if (!item) return;
  const res = await fetch('/api/save', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ bm: STATE.bm, review_id: item.review_id, clear: true })
  }).then(r => r.json());
  if (res.ok) {
    item.label = {};
    item.is_labelled = false;
    STATE.data[STATE.bm].labelled_count = res.labelled_count;
    updateBadges();
    renderCurrent();
  }
}

function prevItem() {
  if (STATE.idx > 0) {
    STATE.idx -= 1;
    renderCurrent();
  }
}

function jumpNextUnlabelled() {
  const d = STATE.data[STATE.bm];
  if (!d) return;
  const nextIdx = d.items.findIndex((it, i) => i > STATE.idx && !it.is_labelled);
  if (nextIdx !== -1) {
    STATE.idx = nextIdx;
    renderCurrent();
    return;
  }
  const firstIdx = d.items.findIndex(it => !it.is_labelled);
  if (firstIdx !== -1) {
    STATE.idx = firstIdx;
    renderCurrent();
  } else {
    alert(`Đã chấm đủ ${d.total}/${d.total} mẫu của ${STATE.bm.toUpperCase()}!`);
  }
}

async function computeAllAgreement() {
  const res = await fetch('/api/score', { method: 'POST' }).then(r => r.json());
  const body = document.getElementById('modal-body');
  let html = '';
  for (const [bmKey, title] of [['hcmut', 'HCMUT Regulations (d2-gpu-r2-4b-hcmut-v1)'], ['labour', 'Labour Law (d2-gpu-r2-4b-labour-v1)']]) {
    const r = res[bmKey];
    html += `<h3 style="margin:14px 0 6px 0;color:#93c5fd">${title}</h3>`;
    if (!r || r.status !== 'ok') {
      html += `<p style="color:#fca5a5">Trạng thái: <strong>${r ? r.status : 'error'}</strong> — ${r && r.detail ? r.detail : 'Cần chấm tối thiểu 10 mẫu (khuyến nghị đủ 30/30 mẫu).'}</p>`;
      continue;
    }
    const jh = r.judge_vs_human;
    html += `<p style="margin:4px 0;font-size:13px;color:#cbd5e1">Đã chấm: <strong>${r.labelled_items}/${r.sample_size}</strong> mẫu. Reviewer: <code>${JSON.stringify(r.reviewers)}</code></p>`;
    html += `<table class="res-table">
      <thead><tr><th>Dimension</th><th>n</th><th>Agreement (%)</th><th>Cohen's κ</th><th>Weighted Agreement (%)</th><th>Weighted κ</th></tr></thead>
      <tbody>`;
    for (const dim of ['strict_success', 'behaviour_appropriate', 'correctness', 'completeness', 'all_claims_supported']) {
      const e = jh[dim];
      if (!e) continue;
      const pct = e.percent_agreement != null ? (e.percent_agreement * 100).toFixed(1) + '%' : 'n/a';
      const kap = e.kappa != null ? e.kappa.toFixed(3) : 'n/a';
      const wpct = e.weighted_percent_agreement != null ? (e.weighted_percent_agreement * 100).toFixed(1) + '%' : 'n/a';
      const wkap = e.weighted_kappa != null ? e.weighted_kappa.toFixed(3) : 'n/a';
      html += `<tr><td><strong>${dim}</strong></td><td>${e.n}</td><td>${pct}</td><td>${kap}</td><td>${wpct}</td><td>${wkap}</td></tr>`;
    }
    html += `</tbody></table>`;
  }
  body.innerHTML = html;
  document.getElementById('modal-backdrop').style.display = 'flex';
}

document.addEventListener('keydown', (e) => {
  if (['INPUT', 'TEXTAREA'].includes(document.activeElement.tagName)) {
    if (e.key === 'Enter') {
      e.preventDefault();
      saveCurrentItem(true);
    }
    return;
  }
  if (e.key === '1') { e.preventDefault(); applyPreset('perfect_answer'); }
  else if (e.key === '2') { e.preventDefault(); applyPreset('valid_refusal'); }
  else if (e.key === '3') { e.preventDefault(); applyPreset('over_refusal'); }
  else if (e.key === '4') { e.preventDefault(); applyPreset('partial_answer'); }
  else if (e.key === 'Enter' || e.key === ']') { e.preventDefault(); saveCurrentItem(true); }
  else if (e.key === '[') { e.preventDefault(); prevItem(); }
});

fetchAll();
</script>
</body>
</html>
"""


class AuditHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:
        return

    def _send_json(self, data: Any, status: int = 200) -> None:
        raw = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            raw = INDEX_HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
            return
        if parsed.path == "/api/data":
            qs = parse_qs(parsed.query)
            bm = (qs.get("bm") or ["hcmut"])[0]
            if bm not in RUNS:
                self._send_json({"error": "Invalid benchmark"}, status=400)
                return
            self._send_json(load_benchmark_data(bm))
            return
        self._send_json({"error": "Not found"}, status=404)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        length = int(self.headers.get("Content-Length") or "0")
        body = json.loads(self.rfile.read(length).decode("utf-8")) if length > 0 else {}
        if parsed.path == "/api/save":
            try:
                bm = body.get("bm", "hcmut")
                res = save_label_row(bm, body)
                self._send_json(res)
            except Exception as exc:
                self._send_json({"ok": False, "error": str(exc)}, status=400)
            return
        if parsed.path == "/api/score":
            try:
                res = run_scorer_all()
                self._send_json(res)
            except Exception as exc:
                self._send_json({"ok": False, "error": str(exc)}, status=400)
            return
        self._send_json({"error": "Not found"}, status=404)


def main() -> None:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    server = ThreadingHTTPServer(("127.0.0.1", port), AuditHandler)
    print(f"Human Audit Web Platform running at http://127.0.0.1:{port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
