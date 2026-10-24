#!/usr/bin/env python3
"""Offline replay of the L1 verifier (v1 vs v2) on recorded answer drafts. No inference, no model server.

Real implementations only (AGENTS.md): the real `LexicalGroundingVerifier` (v1) and `LexicalGroundingVerifierV2` run
on the real corpus records, with the answer text and citations the controller actually produced (ledger.llm_calls),
parsed by the production `parse_model_citations`, and the retrieved ids recorded in the ledger.

Sub-commands
  replay   every recorded answer draft of the D2 v3 L1 / L1+rerank trials and the final answer of every OFF trial:
           failure reasons for v1 vs v2, agreement of the v1 replay with what the run recorded, and (when the judge
           output exists under <run>/judge/judgments.jsonl) a confusion table of L1 pass/fail vs judge strict
           correctness.
  dev      the development set: bll2019-main-v2 answers with the deepseek-judge-main-v1 labels. Sweeps the v2 support
           threshold and applies the a-priori selection rule (see SELECTION_RULE).

The judge labels of the v3 runs are only read by `replay`'s final confusion table. They never choose a threshold or a
rule: the threshold comes from `dev` (bll2019) alone.

Examples (repo root):
  python evaluation/probes/l1_replay.py dev    --out evaluation/runs/l1-replay-2026-10-24
  python evaluation/probes/l1_replay.py replay --out evaluation/runs/l1-replay-2026-10-24
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from src.agent.citations import parse_model_citations  # noqa: E402
from src.domains import load_profile  # noqa: E402
from src.verifier.lexical_grounding import LexicalGroundingVerifier, _quantity_key, split_sentences  # noqa: E402
from src.verifier.lexical_grounding_v2 import DEFAULT_SUPPORT_THRESHOLD, LexicalGroundingVerifierV2  # noqa: E402

RUNS = REPO / "evaluation" / "runs"
V3_RUNS = ["d2-gpu-main-hcmut-v3", "d2-gpu-main-labour-v3"]
DEV_RUN, DEV_JUDGE = "bll2019-main-v2", "deepseek-judge-main-v1"
DEV_CORPUS, DEV_PROFILE = "data/corpus/labor_code_2019_official.json", "labour_vi_2019"
GRID = [0.2, 0.3, 0.4, 0.5, 0.6]
SELECTION_RULE = ("Chosen a priori, before any v3 label existed: the largest value of the grid {0.2, 0.3, 0.4, 0.5, 0.6} "
                  "for which L1 v2 rejects no answer that the judge scored strictly correct on the bll2019 development "
                  "set (a repair loop that rejects correct answers only wastes the controller's budget).")
V1_THRESHOLD = 0.25   # l1_overlap_threshold of the frozen configs (config/config.yaml and config/benchmark/*)

REASONS = ["empty_answer", "missing_citation", "unknown_citation", "unretrieved_citation", "quote_mismatch",
           "quantity", "claim_unsupported"]


# --- v1 reason codes (v1 itself only returns feedback text) ----------------------------------------------------

def v1_reasons(v1: LexicalGroundingVerifier, answer: str, citations: list, retrieved: List[str]) -> Tuple[bool, List[str], str]:
    """(is_valid, reason codes, feedback) of the unchanged v1 verifier. The codes are recomputed with v1's own rules;
    the result of `verify` itself is returned untouched."""
    result = v1.verify(answer, citations, retrieved)
    if result.is_valid:
        return True, [], ""
    messages = v1.profile.messages
    if not answer or not answer.strip():
        return False, ["empty_answer"], result.repair_feedback
    if not citations:
        return False, ["missing_citation"], result.repair_feedback
    codes: List[str] = []
    if result.invalid_citations:
        for text in result.invalid_citations:
            if text.startswith(messages.l1_unknown_citation.split("'")[0]) and "không tồn tại trong cơ sở tri thức" in text:
                codes.append("unknown_citation")
            elif text.startswith(messages.l1_quote_mismatch.split("'")[0]) and "không nằm trong văn bản nguồn" in text:
                codes.append("quote_mismatch")
            else:
                codes.append("unretrieved_citation")
        return False, codes, result.repair_feedback
    # sentence stage: quantity vs overlap, with v1's own rule
    texts = []
    for c in citations:
        doc = v1.valid_article_ids.get(v1._normalize_id(c.article_id))
        if doc:
            title = doc.get("title") or ""
            content = doc.get("content") or doc.get("full_content") or ""
            texts.append((f"{title}. {content}" if title else content).lower())
    source = " ".join(texts)
    source_quantities = {_quantity_key(q) for q in re.findall(v1.profile.quantity_pattern, source)}
    for sentence in result.unsupported_claims:
        quantities = {_quantity_key(q) for q in re.findall(v1.profile.quantity_pattern, sentence.lower())}
        codes.append("quantity" if quantities - source_quantities else "claim_unsupported")
    return False, codes, result.repair_feedback


def v2_reasons(report) -> List[str]:
    out = []
    for kind in report.reasons:
        out.append("quantity" if kind.startswith("quantity_") else kind)
    return out


# --- recorded trials -------------------------------------------------------------------------------------------

def answer_drafts(ledger: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [c["response"]["tool_args"] for c in ledger.get("llm_calls", [])
            if isinstance(c.get("response"), dict) and c["response"].get("action") == "answer"
            and isinstance(c["response"].get("tool_args"), dict)]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def strict_success(judgment: Dict[str, Any], system_error: bool) -> Optional[bool]:
    """Same definition as evaluation/analyze_judge.py: judgeable, appropriate behaviour, correctness 2, completeness 2,
    every claim supported. None = no usable judgment."""
    if judgment is None or not judgment.get("judgeable"):
        return None
    return bool(not system_error and judgment["behaviour_appropriate"] and judgment["correctness"] == 2
                and judgment["completeness"] == 2 and all(c["support"] == "supported" for c in judgment["claims"]))


# --- confusion table ---------------------------------------------------------------------------------------------

def confusion(rows: List[Dict[str, Any]], version: str) -> Dict[str, Any]:
    """rows: dicts with `<version>_pass` (bool) and `correct` (bool). Rates are conditional on the label."""
    tp = sum(r[f"{version}_pass"] and r["correct"] for r in rows)       # pass & correct
    fp = sum(r[f"{version}_pass"] and not r["correct"] for r in rows)   # pass & incorrect
    fn = sum((not r[f"{version}_pass"]) and r["correct"] for r in rows)  # reject & correct
    tn = sum((not r[f"{version}_pass"]) and not r["correct"] for r in rows)
    ratio = lambda a, b: (a / b) if b else None  # noqa: E731
    return {"n": len(rows), "pass_correct": tp, "pass_incorrect": fp, "reject_correct": fn, "reject_incorrect": tn,
            "precision_of_pass": ratio(tp, tp + fp), "rejection_rate_of_incorrect": ratio(tn, tn + fp),
            "rejection_rate_of_correct": ratio(fn, fn + tp)}


# --- dev set ---------------------------------------------------------------------------------------------------

def dev_rows() -> List[Dict[str, Any]]:
    profile = load_profile(DEV_PROFILE)
    runs = load_jsonl(RUNS / DEV_RUN / "runs.jsonl")
    details = {(d["task_id"], d["seed"], d["mode"]): d
               for d in load_json(RUNS / DEV_JUDGE / "analysis-final" / "private-judge-details.json")}
    rows = []
    for r in runs:
        ledger = r["ledger"]
        final = ledger.get("final_output") or {}
        if final.get("action") != "answer":
            continue
        detail = details[(r["task_id"], r["seed"], r["mode"])]
        success = detail["llm_task_success_estimate"]
        if success is None:
            continue                     # no usable judgment (counted by the caller)
        drafts = answer_drafts(ledger)
        if not drafts:
            continue
        draft = drafts[-1]
        rows.append({"task_id": r["task_id"], "seed": r["seed"], "mode": r["mode"], "answer": draft.get("content", ""),
                     "citations": parse_model_citations(profile, draft.get("citations", [])),
                     "retrieved": ledger["retrieved_article_ids"], "correct": bool(success),
                     "judge_correctness": detail["judgment"]["correctness"]})
    return rows


def run_dev(out: Path) -> Dict[str, Any]:
    corpus = load_json(REPO / DEV_CORPUS)
    profile = load_profile(DEV_PROFILE)
    rows = dev_rows()
    v1 = LexicalGroundingVerifier(corpus, overlap_threshold=V1_THRESHOLD, profile=profile)
    for r in rows:
        r["v1_pass"] = v1.verify(r["answer"], r["citations"], r["retrieved"]).is_valid
    sweep: Dict[str, Any] = {}
    for tau in GRID:
        verifier = LexicalGroundingVerifierV2(corpus, profile=profile, support_threshold=tau)
        for r in rows:
            report = verifier.analyze(r["answer"], r["citations"], r["retrieved"])
            r[f"v2_pass@{tau}"] = report.passed
            r[f"v2_reasons@{tau}"] = v2_reasons(report)
        sweep[str(tau)] = {
            "all": confusion([{**r, "v2_pass": r[f"v2_pass@{tau}"]} for r in rows], "v2"),
            "off_only": confusion([{**r, "v2_pass": r[f"v2_pass@{tau}"]} for r in rows if r["mode"] == "off"], "v2"),
            "reasons": dict(Counter(x for r in rows for x in r[f"v2_reasons@{tau}"]))}
    selected = None
    for tau in GRID:
        if sweep[str(tau)]["all"]["reject_correct"] == 0:
            selected = tau
    summary = {
        "set": f"{DEV_RUN} final answers with labels from {DEV_JUDGE} (strict success, see strict_success)",
        "n_answers": len(rows), "n_strictly_correct": sum(r["correct"] for r in rows),
        "n_not_strictly_correct": sum(not r["correct"] for r in rows),
        "n_off": sum(r["mode"] == "off" for r in rows), "n_l1_on": sum(r["mode"] == "l1_on" for r in rows),
        "caveat": ("l1_on finals already passed v1 (selection); off finals are unselected. Small set from one 3B model; "
                   "the threshold is a coarse a-priori choice, not a calibrated optimum."),
        "selection_rule": SELECTION_RULE, "selected_threshold": selected, "default_in_code": DEFAULT_SUPPORT_THRESHOLD,
        "v1_baseline": {"all": confusion([{**r, "v2_pass": r["v1_pass"]} for r in rows], "v2"),
                        "off_only": confusion([{**r, "v2_pass": r["v1_pass"]} for r in rows if r["mode"] == "off"], "v2")},
        "v2_sweep": sweep,
        "per_answer": [{k: v for k, v in r.items() if k not in ("answer", "citations", "retrieved")
                        and not k.startswith("v2_reasons@")} for r in rows]}
    (out / "dev_bll2019.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


# --- v3 replay -------------------------------------------------------------------------------------------------

def run_replay(out: Path, tau: float) -> Dict[str, Any]:
    drafts_out: List[Dict[str, Any]] = []
    agreement: Counter = Counter()
    mismatches: List[Dict[str, Any]] = []
    judged_rows: List[Dict[str, Any]] = []
    judge_found: Dict[str, int] = {}
    for run_name in V3_RUNS:
        run_dir = RUNS / run_name
        manifest = load_json(run_dir / "manifest.json")
        benchmarks = {b["name"]: b for b in manifest["benchmarks"]}
        verifiers: Dict[str, Tuple[Any, Any, Any]] = {}
        for name, b in benchmarks.items():
            profile = load_profile(b["profile"])
            corpus = load_json(REPO / b["corpus"])
            verifiers[name] = (profile,
                               LexicalGroundingVerifier(corpus, overlap_threshold=V1_THRESHOLD, profile=profile),
                               LexicalGroundingVerifierV2(corpus, profile=profile, support_threshold=tau))
        labels = load_labels(run_dir)
        judge_found[run_name] = len(labels)
        for trial in load_jsonl(run_dir / "trials.jsonl"):
            if trial["variant"] not in ("off", "l1", "l1_rerank") or trial.get("warmup"):
                continue
            ledger = trial["ledger"]
            drafts = answer_drafts(ledger)
            if not drafts:
                continue
            profile, v1, v2 = verifiers[trial["benchmark"]]
            repairs = [e.get("feedback") for e in ledger["audit_events"] if e.get("event") == "repair"]
            final = ledger.get("final_output") or {}
            key = (trial["benchmark"], trial["variant"], trial["seed"], trial["task_id"], trial.get("attempt", 1))
            retrieved = ledger["retrieved_article_ids"]
            for i, draft in enumerate(drafts):
                answer = draft.get("content", "")
                citations = parse_model_citations(profile, draft.get("citations", []))
                ok1, codes1, feedback1 = v1_reasons(v1, answer, citations, retrieved)
                report = v2.analyze(answer, citations, retrieved)
                is_last = i == len(drafts) - 1
                if trial["variant"] == "off":
                    recorded = "unverified"
                elif i < len(repairs):
                    recorded = "repair"
                elif is_last and final.get("action") == "answer":
                    recorded = "accepted"
                else:
                    recorded = "refused_after_repairs" if final.get("action") == "refuse" else "other"
                # agreement of the unchanged v1 with what the run recorded (provenance caveat: final retrieved list)
                if recorded == "repair":
                    same = (not ok1) and feedback1 == repairs[i]
                elif recorded == "accepted":
                    same = ok1
                elif recorded == "refused_after_repairs":
                    same = (not ok1) and feedback1 in str(final.get("reason", ""))
                else:
                    same = None
                if same is not None:
                    agreement[(trial["variant"], recorded, bool(same))] += 1
                    if not same:
                        mismatches.append({"key": list(key), "draft": i, "recorded": recorded, "v1_valid": ok1,
                                           "v1_feedback": feedback1[:300],
                                           "recorded_feedback": (repairs[i] if recorded == "repair" else str(final.get("reason", "")))[:300]})
                drafts_out.append({
                    "run": run_name, "benchmark": trial["benchmark"], "variant": trial["variant"], "seed": trial["seed"],
                    "task_id": trial["task_id"], "attempt": trial.get("attempt", 1), "draft": i, "n_drafts": len(drafts),
                    "recorded": recorded, "v1_pass": ok1, "v1_reasons": codes1, "v2_pass": report.passed,
                    "v2_reasons": v2_reasons(report), "v2_kinds": report.reasons,
                    "v2_min_coverage": min((s["coverage"] for s in report.sentences), default=None),
                    "v1_feedback_chars": len(feedback1) if not ok1 else 0,
                    "v2_feedback_chars": 0 if report.passed else len(v2.verify(answer, citations, retrieved).repair_feedback)})
                if is_last and final.get("action") == "answer" and key in labels and labels[key] is not None:
                    judged_rows.append({"run": run_name, "variant": trial["variant"], "benchmark": trial["benchmark"],
                                        "task_id": trial["task_id"], "seed": trial["seed"], "v1_pass": ok1,
                                        "v2_pass": report.passed, "correct": labels[key]})
    with (out / "drafts.jsonl").open("w", encoding="utf-8") as fh:
        for row in drafts_out:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    write_feedback_examples(out, drafts_out)

    def reason_table(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
        table: Dict[str, Any] = {"drafts": len(rows)}
        for version in ("v1", "v2"):
            fails = [r for r in rows if not r[f"{version}_pass"]]
            counts = Counter(x for r in fails for x in set(r[f"{version}_reasons"]))
            table[version] = {"drafts_failing": len(fails), "by_reason_drafts": {k: counts.get(k, 0) for k in REASONS}}
        table["v2_kinds"] = dict(Counter(k for r in rows for k in r["v2_kinds"]))
        for version in ("v1", "v2"):
            sizes = sorted(r[f"{version}_feedback_chars"] for r in rows if not r[f"{version}_pass"])
            table[version]["repair_feedback_chars"] = ({"n": len(sizes), "median": sizes[len(sizes) // 2], "p90": sizes[int(len(sizes) * 0.9)],
                                                        "max": sizes[-1]} if sizes else None)
        return table

    groups = {
        "l1_and_l1_rerank_all_drafts": [r for r in drafts_out if r["variant"] in ("l1", "l1_rerank")],
        "off_final_answers": [r for r in drafts_out if r["variant"] == "off"]}
    for run_name in V3_RUNS:
        groups[f"{run_name}:l1_and_l1_rerank_all_drafts"] = [r for r in groups["l1_and_l1_rerank_all_drafts"] if r["run"] == run_name]
        groups[f"{run_name}:off_final_answers"] = [r for r in groups["off_final_answers"] if r["run"] == run_name]
    summary: Dict[str, Any] = {
        "support_threshold_v2": tau, "v1_overlap_threshold": V1_THRESHOLD,
        "reasons": {name: reason_table(rows) for name, rows in groups.items()},
        "v1_replay_vs_recorded": {f"{v}|{rec}|{'agree' if ok else 'differ'}": n for (v, rec, ok), n in sorted(agreement.items())},
        "v1_replay_mismatches": mismatches[:50], "n_v1_replay_mismatches": len(mismatches),
        "judgments_found": judge_found,
        "paired_v1_v2_pass": {g: {f"v1_{'pass' if a else 'fail'}|v2_{'pass' if b else 'fail'}": sum(
            r["v1_pass"] == a and r["v2_pass"] == b for r in rows) for a in (True, False) for b in (True, False)}
            for g, rows in {**groups, "l1_and_l1_rerank_drafts_accepted_in_the_run_by_v1": [r for r in drafts_out if r["recorded"] == "accepted"]}.items()}}
    if judged_rows:
        summary["confusion_vs_judge_strict"] = {
            "definition": "correct = judge strict success (judgeable, behaviour appropriate, correctness 2, completeness 2, all claims supported); rows = final answers",
            "off_final_answers (unselected)": {v: confusion([r for r in judged_rows if r["variant"] == "off"], v)
                                               for v in ("v1", "v2")},
            "l1_and_l1_rerank_final_answers (already passed v1 in the run: selected)": {
                v: confusion([r for r in judged_rows if r["variant"] != "off"], v) for v in ("v1", "v2")},
            "by_benchmark_off": {b: {v: confusion([r for r in judged_rows if r["variant"] == "off" and r["benchmark"] == b], v)
                                     for v in ("v1", "v2")} for b in sorted({r["benchmark"] for r in judged_rows})}}
    else:
        summary["confusion_vs_judge_strict"] = "no judge output under evaluation/runs/d2-gpu-main-*-v3/judge/judgments.jsonl at replay time"
    (out / "replay_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def write_feedback_examples(out: Path, drafts_out: List[Dict[str, Any]]) -> None:
    """First failing L1 / L1+rerank draft per (benchmark, v2 finding kind): the answer, v1 feedback, v2 feedback."""
    profiles: Dict[str, Tuple[Any, Any, Any]] = {}
    seen, lines = set(), []
    for row in drafts_out:
        if row["variant"] not in ("l1", "l1_rerank") or row["v2_pass"]:
            continue
        kind = row["v2_kinds"][0]
        if (row["benchmark"], kind) in seen:
            continue
        seen.add((row["benchmark"], kind))
        run_dir = RUNS / row["run"]
        b = {x["name"]: x for x in load_json(run_dir / "manifest.json")["benchmarks"]}[row["benchmark"]]
        if row["benchmark"] not in profiles:
            profile = load_profile(b["profile"])
            corpus = load_json(REPO / b["corpus"])
            profiles[row["benchmark"]] = (profile, LexicalGroundingVerifier(corpus, overlap_threshold=V1_THRESHOLD, profile=profile),
                                          LexicalGroundingVerifierV2(corpus, profile=profile))
        profile, v1, v2 = profiles[row["benchmark"]]
        for trial in load_jsonl(run_dir / "trials.jsonl"):
            if (trial["benchmark"], trial["variant"], trial["seed"], trial["task_id"], trial.get("attempt", 1)) == \
                    (row["benchmark"], row["variant"], row["seed"], row["task_id"], row["attempt"]):
                draft = answer_drafts(trial["ledger"])[row["draft"]]
                citations = parse_model_citations(profile, draft.get("citations", []))
                retrieved = trial["ledger"]["retrieved_article_ids"]
                lines.append(json.dumps({
                    "benchmark": row["benchmark"], "task_id": row["task_id"], "variant": row["variant"], "seed": row["seed"],
                    "draft": row["draft"], "v2_kinds": row["v2_kinds"], "answer": draft.get("content", ""),
                    "citations": [c.model_dump() for c in citations], "v1_feedback": v1.verify(draft.get("content", ""), citations, retrieved).repair_feedback,
                    "v2_feedback": v2.verify(draft.get("content", ""), citations, retrieved).repair_feedback}, ensure_ascii=False))
                break
    (out / "feedback_examples.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")


def load_labels(run_dir: Path) -> Dict[Tuple, Optional[bool]]:
    """(benchmark, variant, seed, task_id, attempt) -> strict success, from <run>/judge/judgments.jsonl; empty if absent."""
    path = run_dir / "judge" / "judgments.jsonl"
    if not path.is_file():
        return {}
    mapping = {m["review_id"]: m for m in load_json(run_dir / "judge" / "private_mapping.json")}
    labels: Dict[Tuple, Optional[bool]] = {}
    for row in load_jsonl(path):
        meta = mapping.get(row["review_id"])
        if meta is None:
            continue
        key = (meta["benchmark"], meta["variant"], meta["seed"], meta["task_id"], meta.get("attempt", 1))
        labels[key] = strict_success(row.get("judgment"), meta.get("system_error", False)) if row.get("status") == "valid" else None
    return labels


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=["dev", "replay"])
    parser.add_argument("--out", required=True)
    parser.add_argument("--tau", type=float, default=DEFAULT_SUPPORT_THRESHOLD, help="v2 support threshold for `replay`")
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    started = datetime.now().astimezone().isoformat()
    result = run_dev(out) if args.command == "dev" else run_replay(out, args.tau)
    print(json.dumps({k: v for k, v in result.items() if k not in ("per_answer", "v1_replay_mismatches")},
                     ensure_ascii=False, indent=2))
    print(f"started {started}; wrote {out}", file=sys.stderr)


if __name__ == "__main__":
    main()
