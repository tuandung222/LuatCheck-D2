"""What the L1 verifier changes, measured on recorded runs (no inference, no new judging).

For every run and system variant (off / l1 / l1_rerank) it counts, on answer-expected tasks: answers given, answers the
judge rated fully correct (correctness 2 and completeness 2), answers containing at least one claim the judge labelled
`contradicted`, refusals after the repair budget was spent, repair rounds and the L1 rejection reasons (from the
feedback text of each repair event), and strict success (same rule as evaluation/judge_rules.py, lower bound).
Judge labels are LLM estimates, not human labels.

    .venv/bin/python evaluation/probes/l1_effect.py --out evaluation/runs/l1-effect-2026-10-24/results.json
"""
import argparse
import json
from collections import Counter
from pathlib import Path

RUNS = {
    "initial 2B / HCMUT": "evaluation/runs/d2-gpu-main-hcmut-v3",
    "initial 2B / Labour": "evaluation/runs/d2-gpu-main-labour-v3",
    "current 2B / HCMUT": "evaluation/runs/d2-gpu-r2-2b-hcmut-v1",
    "current 2B / Labour": "evaluation/runs/d2-gpu-r2-2b-labour-v1",
    "current 4B / HCMUT": "evaluation/runs/d2-gpu-r2-4b-hcmut-v1",
    "current 4B / Labour": "evaluation/runs/d2-gpu-r2-4b-labour-v1",
}
VARIANTS = ("off", "l1", "l1_rerank")
# Feedback wording of each L1 check (config/domains/messages/vi.yaml), most specific first.
REASONS = [
    ("quote not verbatim (v2, other record)", "nằm trong '"),
    ("quote not verbatim", "exact_quote"),
    ("quote not verbatim", "Trích nguyên văn"),
    ("number not in the matching source sentence", "Số liệu '"),
    ("unknown document id", "không tồn tại trong cơ sở tri thức"),
    ("cited document never retrieved", "chưa được"),
    ("missing citation", "không cung cấp bất kỳ trích dẫn"),
    ("sentence without support", "chưa có căn cứ"),
    ("sentence without support", "chưa tìm thấy căn cứ"),
]


def judgments(run: Path):
    mapping = {m["review_id"]: m for m in json.loads((run / "judge/private_mapping.json").read_text(encoding="utf-8"))}
    valid = {}
    for line in (run / "judge/judgments.jsonl").read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        if row.get("status") == "valid":
            j = row["judgment"]
            valid[row["review_id"]] = j if isinstance(j, dict) else json.loads(j)
    return {(m["variant"], m["seed"], m["task_id"]): valid.get(rid) for rid, m in mapping.items()}


def strict(trial, j) -> bool:
    if trial["system_error"] or not j or not j.get("judgeable"):
        return False
    abst = trial["expected_behavior"] == "refuse" or trial["terminal_status"] in ("refused", "clarified")
    claims = [c for c in j["claims"] if not (abst and c["support"] == "not_established")]
    return bool(j["behaviour_appropriate"] and j["correctness"] == 2 and j["completeness"] == 2
                and all(c["support"] == "supported" for c in claims))


def reason_of(feedback: str) -> str:
    for label, needle in REASONS:
        if needle in feedback:
            return label
    return "other"


def measure(run: Path):
    judged = judgments(run)
    cells = {}
    for line in (run / "trials.jsonl").read_text(encoding="utf-8").splitlines():
        t = json.loads(line)
        v = t["variant"]
        if v not in VARIANTS:
            continue
        c = cells.setdefault(v, Counter())
        c["trials"] += 1
        j = judged.get((v, t["seed"], t["task_id"]))
        c["strict_success"] += strict(t, j)
        events = t["ledger"].get("audit_events") or []
        repairs = [e for e in events if e.get("event") == "repair"]
        c["repair_rounds"] += len(repairs)
        c["trials_with_repair"] += bool(repairs)
        for e in repairs:
            c["reason: " + reason_of(str(e.get("feedback", "")))] += 1
        c["l1_warnings"] += sum(1 for e in events if e.get("event") == "l1_warning")
        if t["expected_behavior"] != "answer":
            continue
        c["answer_tasks"] += 1
        status = t["terminal_status"]
        c[f"status: {status}"] += 1
        if status == "refused" and t["ledger"].get("refusal_source") == "repair_exhausted":
            c["refused_after_repairs"] += 1
        if status == "answered" and repairs:
            c["answered_after_repair"] += 1
        if status == "answered" and j and j.get("judgeable"):
            c["answered_judged"] += 1
            c["answered_fully_correct"] += j["correctness"] == 2 and j["completeness"] == 2
            c["answered_with_contradicted_claim"] += any(x["support"] == "contradicted" for x in j["claims"])
    return {v: dict(cells[v]) for v in VARIANTS if v in cells}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    results = {label: measure(Path(path)) for label, path in RUNS.items()}
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"runs": RUNS, "results": results}, ensure_ascii=False, indent=1), encoding="utf-8")
    for label, cells in results.items():
        print(label)
        for v, c in cells.items():
            n = max(c.get("answered_judged", 0), 1)
            print(f"  {v:10} strict {100 * c['strict_success'] / c['trials']:5.1f}%  answered {c.get('status: answered', 0):3}/{c['answer_tasks']}"
                  f"  fully-correct {100 * c.get('answered_fully_correct', 0) / n:4.0f}%  contradicted {c.get('answered_with_contradicted_claim', 0):3}"
                  f"  repairs {c['repair_rounds']:3}  refused-after-repairs {c.get('refused_after_repairs', 0)}")


if __name__ == "__main__":
    main()
