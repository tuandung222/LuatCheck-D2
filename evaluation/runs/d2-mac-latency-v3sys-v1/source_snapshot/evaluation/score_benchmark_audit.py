"""Judge-vs-human agreement for a D2 benchmark run (percent agreement and Cohen's kappa), from REAL human labels only.

Input  : the human-audit export of a judged run (<run>/analysis/human-audit/, written by judge_benchmark.py analyze) and
         one or more filled copies of its labels.csv (columns: review_id, reviewer, judgeable, behaviour_appropriate,
         correctness, completeness, total_claims, unsupported_claims, notes). One row per (reviewer, item).
Output : <run>/analysis/human-audit/agreement.json (+ agreement.md). Status is one of
           ok                 numbers computed
           no_labels          every label row is blank: NO numbers are produced
           insufficient_labels fewer labelled items than --min-items: NO numbers are produced
           invalid_labels     malformed rows: listed, NO numbers are produced
Nothing is ever imputed, defaulted or generated: blank cells are missing, a half-filled row is an error, and an item the
sample does not contain is an error. The scorer reads the judge's verdicts only AFTER the human labels are validated.

Definitions (same rubric as the judge, see evaluation/judge_prompt.txt)
  strict success = judgeable AND behaviour_appropriate AND correctness == 2 AND completeness == 2 AND unsupported_claims == 0
  all_claims_supported = unsupported_claims == 0 (judge: every counted claim labelled `supported`)
  A refusal / abstention / "no information in the sources" sentence is not a factual claim: reviewers leave it out of total_claims and
  unsupported_claims, and for abstention outputs the judge side ignores `not_established` claims (evaluation/judge_rules.py).
Agreement is reported for: judgeable, behaviour_appropriate, correctness (nominal and linear-weighted kappa), completeness
(same), all_claims_supported and strict_success (the last four over items both raters consider judgeable).
The audit sample is stratified (benchmark x variant x category x judge outcome), so unweighted agreement describes the sample;
when stratum sizes are available a design-weighted percent agreement / kappa is added (weight = stratum size / sampled in stratum).
With several reviewers, judge_vs_human pools every (reviewer, item) label (an item labelled twice counts twice) and
per_reviewer / human_vs_human are given separately.
"""
import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from evaluation import judge_rules, stats

LABEL_COLUMNS = ["review_id", "reviewer", "judgeable", "behaviour_appropriate", "correctness", "completeness",
                 "total_claims", "unsupported_claims", "notes"]
FIELDS = LABEL_COLUMNS[2:8]
TRUE = {"1", "true", "yes", "y", "t", "co", "có"}
FALSE = {"0", "false", "no", "n", "f", "khong", "không"}
EXIT = {"ok": 0, "no_labels": 3, "invalid_labels": 4, "insufficient_labels": 5}


def parse_bool(text: str) -> Optional[bool]:
    value = text.strip().lower()
    return True if value in TRUE else False if value in FALSE else None


def parse_int(text: str, low: int, high: Optional[int] = None) -> Optional[int]:
    value = text.strip()
    if not value.lstrip("-").isdigit():
        return None
    number = int(value)
    return number if number >= low and (high is None or number <= high) else None


def load_labels(paths: List[Path], sample_ids: List[str]) -> Tuple[List[Dict[str, Any]], List[str], int]:
    """(valid label records, problems, blank rows). A row with every label field blank is a missing label, not an error."""
    problems: List[str] = []
    records: List[Dict[str, Any]] = []
    blank = 0
    seen: set = set()
    sample = set(sample_ids)
    for path in paths:
        with open(path, newline="", encoding="utf-8") as stream:
            reader = csv.DictReader(stream)
            missing_columns = [c for c in LABEL_COLUMNS[:-1] if c not in (reader.fieldnames or [])]
            if missing_columns:
                problems.append(f"{path}: missing columns {missing_columns}")
                continue
            for line_number, row in enumerate(reader, start=2):
                where = f"{path.name}:{line_number}"
                rid = (row.get("review_id") or "").strip()
                if not any((row.get(f) or "").strip() for f in FIELDS):
                    blank += 1
                    continue
                reviewer = (row.get("reviewer") or "").strip()
                if not reviewer:
                    problems.append(f"{where}: labels present but `reviewer` is blank (the labeller must be recorded)")
                    continue
                if rid not in sample:
                    problems.append(f"{where}: review_id {rid!r} is not in the audit sample of this run")
                    continue
                if (reviewer, rid) in seen:
                    problems.append(f"{where}: duplicate label by {reviewer!r} for {rid}")
                    continue
                judgeable = parse_bool(row.get("judgeable") or "")
                if judgeable is None:
                    problems.append(f"{where}: `judgeable` must be 1/0 (yes/no), got {row.get('judgeable')!r}")
                    continue
                record: Dict[str, Any] = {"review_id": rid, "reviewer": reviewer, "judgeable": judgeable, "notes": row.get("notes", "")}
                if judgeable:
                    behaviour = parse_bool(row.get("behaviour_appropriate") or "")
                    correctness = parse_int(row.get("correctness") or "", 0, 2)
                    completeness = parse_int(row.get("completeness") or "", 0, 2)
                    total = parse_int(row.get("total_claims") or "", 0)
                    unsupported = parse_int(row.get("unsupported_claims") or "", 0, total if total is not None else None)
                    bad = [name for name, v in (("behaviour_appropriate", behaviour), ("correctness", correctness), ("completeness", completeness),
                                                ("total_claims", total), ("unsupported_claims", unsupported)) if v is None]
                    if bad:
                        problems.append(f"{where}: judgeable item has missing/invalid {bad} (behaviour 1/0, correctness/completeness 0-2, "
                                        "total_claims >= 0, 0 <= unsupported_claims <= total_claims)")
                        continue
                    record.update(behaviour_appropriate=behaviour, correctness=correctness, completeness=completeness,
                                  total_claims=total, unsupported_claims=unsupported,
                                  all_claims_supported=unsupported == 0,
                                  strict_success=bool(behaviour and correctness == 2 and completeness == 2 and unsupported == 0))
                seen.add((reviewer, rid))
                records.append(record)
    return records, problems, blank


def judge_verdicts(run_dir: Path) -> Dict[str, Dict[str, Any]]:
    path = run_dir / "judge" / "judgments.jsonl"
    if not path.is_file():
        raise FileNotFoundError(f"{path} not found: the run has not been judged")
    packets = {p["review_id"]: p for p in json.loads((run_dir / "judge" / "judge_packets.json").read_text(encoding="utf-8"))}
    out: Dict[str, Dict[str, Any]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        j = row.get("judgment")
        if row.get("status") != "valid" or not j:
            continue
        verdict: Dict[str, Any] = {"judgeable": bool(j["judgeable"])}
        if j["judgeable"]:
            packet = packets[row["review_id"]]
            abstention = judge_rules.is_abstention(packet["expected_behavior"], packet["candidate_behavior"])
            counted = judge_rules.counted_claims(j["claims"], abstention)
            unsupported = len(judge_rules.unsupported_claims(j["claims"], abstention))
            verdict.update(behaviour_appropriate=bool(j["behaviour_appropriate"]), correctness=j["correctness"], completeness=j["completeness"],
                           total_claims=len(counted), unsupported_claims=unsupported, all_claims_supported=unsupported == 0,
                           strict_success=judge_rules.judgment_strict_success(j, abstention))
        out[row["review_id"]] = verdict
    return out


def stratum_weights(run_dir: Path, sample_ids: List[str]) -> Optional[Dict[str, float]]:
    """Design weights N_h / n_h per sampled item, with strata = benchmark x variant x category x judge outcome (the strata the
    sample was drawn from). None when the private trial details are not available."""
    path = run_dir / "analysis" / "private-trial-details.json"
    if not path.is_file():
        return None
    details = json.loads(path.read_text(encoding="utf-8"))
    eligible = [d for d in details if d.get("judgment") is not None and d.get("judgeable")]
    key = lambda d: (d["benchmark"], d["variant"], d["category"], str(d["success"]))
    population = Counter(key(d) for d in eligible)
    by_id = {d["review_id"]: key(d) for d in eligible}
    sampled = Counter(by_id[r] for r in sample_ids if r in by_id)
    if any(r not in by_id for r in sample_ids):
        return None
    return {r: population[by_id[r]] / sampled[by_id[r]] for r in sample_ids}


def compare(pairs: List[Tuple[Dict[str, Any], Dict[str, Any]]], weights: Optional[Dict[str, float]]) -> Dict[str, Any]:
    """pairs of (judge verdict, human record) for the same item."""
    out: Dict[str, Any] = {}
    w_all = [weights[h["review_id"]] for _, h in pairs] if weights else None
    out["judgeable"] = stats.agreement_summary([j["judgeable"] for j, _ in pairs], [h["judgeable"] for _, h in pairs], w_all)
    both = [(j, h) for j, h in pairs if j["judgeable"] and h["judgeable"]]
    w_both = [weights[h["review_id"]] for _, h in both] if weights else None
    out["items_both_judgeable"] = len(both)
    if both:
        for name in ("behaviour_appropriate", "all_claims_supported", "strict_success"):
            out[name] = stats.agreement_summary([j[name] for j, _ in both], [h[name] for _, h in both], w_both)
        for name in ("correctness", "completeness"):
            x, y = [j[name] for j, _ in both], [h[name] for _, h in both]
            out[name] = stats.agreement_summary(x, y, w_both, "nominal", [0, 1, 2])
            out[name]["kappa_linear_weighted"] = stats.cohen_kappa(x, y, scheme="linear", order=[0, 1, 2])["kappa"]
        out["unsupported_claims_mean_abs_difference"] = stats.mean([abs(j["unsupported_claims"] - h["unsupported_claims"]) for j, h in both])
        out["judge_strict_success_rate_on_items"] = stats.mean([float(j["strict_success"]) for j, _ in both])
        out["human_strict_success_rate_on_items"] = stats.mean([float(h["strict_success"]) for _, h in both])
    return out


def human_vs_human(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    by_item: Dict[str, Dict[str, Dict[str, Any]]] = defaultdict(dict)
    for r in records:
        by_item[r["review_id"]][r["reviewer"]] = r
    reviewers = sorted({r["reviewer"] for r in records})
    out: Dict[str, Any] = {}
    for i, a in enumerate(reviewers):
        for b in reviewers[i + 1:]:
            shared = [(v[a], v[b]) for v in by_item.values() if a in v and b in v]
            if shared:
                entry = {"items": len(shared), "judgeable": stats.agreement_summary([x["judgeable"] for x, _ in shared], [y["judgeable"] for _, y in shared])}
                both = [(x, y) for x, y in shared if x["judgeable"] and y["judgeable"]]
                if both:
                    entry["strict_success"] = stats.agreement_summary([x["strict_success"] for x, _ in both], [y["strict_success"] for _, y in both])
                    entry["behaviour_appropriate"] = stats.agreement_summary([x["behaviour_appropriate"] for x, _ in both], [y["behaviour_appropriate"] for _, y in both])
                out[f"{a} vs {b}"] = entry
    return out


def score(run_dir: Path, label_paths: List[Path], min_items: int = 10) -> Dict[str, Any]:
    audit_dir = run_dir / "analysis" / "human-audit"
    packets = json.loads((audit_dir / "packets.json").read_text(encoding="utf-8"))
    sample_ids = [p["review_id"] for p in packets]
    result: Dict[str, Any] = {"run_id": json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))["run_id"],
                              "sample_size": len(sample_ids), "label_files": [str(p) for p in label_paths], "min_items": min_items,
                              "judge_vs_human": None, "per_reviewer": None, "human_vs_human": None,
                              "note": "Agreement of the LLM judge with people on a stratified sample; not a population estimate unless the weighted figures are used."}
    records, problems, blank = load_labels(label_paths, sample_ids)
    result.update(problems=problems, blank_rows=blank, label_rows_valid=len(records))
    if problems:
        result["status"] = "invalid_labels"
        return result
    if not records:
        result["status"] = "no_labels"
        result["detail"] = "All label rows are blank: agreement and kappa are not computed."
        return result
    labelled_items = len({r["review_id"] for r in records})
    result["labelled_items"] = labelled_items
    result["coverage"] = labelled_items / len(sample_ids)
    result["reviewers"] = dict(Counter(r["reviewer"] for r in records))
    if labelled_items < min_items:
        result["status"] = "insufficient_labels"
        result["detail"] = f"{labelled_items} labelled items < --min-items {min_items}: numbers withheld."
        return result
    verdicts = judge_verdicts(run_dir)
    unjudged = sorted({r["review_id"] for r in records if r["review_id"] not in verdicts})
    if unjudged:
        result["status"] = "invalid_labels"
        result["problems"] = [f"no valid judge verdict for labelled item {rid}" for rid in unjudged]
        return result
    weights = stratum_weights(run_dir, sample_ids)
    pairs = [(verdicts[r["review_id"]], r) for r in records]
    result["status"] = "ok"
    result["weights_available"] = weights is not None
    result["judge_vs_human"] = compare(pairs, weights)
    result["per_reviewer"] = {name: compare([(verdicts[r["review_id"]], r) for r in records if r["reviewer"] == name], weights)
                              for name in sorted({r["reviewer"] for r in records})}
    result["human_vs_human"] = human_vs_human(records) if len(result["reviewers"]) > 1 else None
    return result


def to_markdown(result: Dict[str, Any]) -> str:
    lines = [f"# Judge vs human agreement - run `{result['run_id']}`", "", f"status: **{result['status']}**"]
    if result["status"] != "ok":
        lines += [result.get("detail", ""), *[f"- {p}" for p in result.get("problems", [])],
                  "", "No agreement or kappa numbers are produced without valid human labels."]
        return "\n".join(lines) + "\n"
    lines += [f"sample {result['sample_size']}, labelled items {result['labelled_items']} ({100 * result['coverage']:.0f}%), reviewers {result['reviewers']}", "",
              "| dimension | n | agreement | kappa | weighted agreement | weighted kappa |", "|---|---|---|---|---|---|"]
    for name, entry in result["judge_vs_human"].items():
        if isinstance(entry, dict) and "percent_agreement" in entry:
            def f(v, d=3):
                return "n/a" if v is None else f"{v:.{d}f}"
            lines.append(f"| {name} | {entry['n']} | {f(entry['percent_agreement'])} | {f(entry['kappa'])} | "
                         f"{f(entry.get('weighted_percent_agreement'))} | {f(entry.get('weighted_kappa'))} |")
    return "\n".join(lines) + "\n"


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--labels", nargs="+", help="filled label CSV(s); default <run>/analysis/human-audit/labels.csv")
    parser.add_argument("--min-items", type=int, default=10, help="minimum labelled items before any number is produced")
    args = parser.parse_args(argv)
    run_dir = Path(args.run_dir)
    paths = [Path(p) for p in args.labels] if args.labels else [run_dir / "analysis" / "human-audit" / "labels.csv"]
    result = score(run_dir, paths, args.min_items)
    out_dir = run_dir / "analysis" / "human-audit"
    (out_dir / "agreement.json").write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    (out_dir / "agreement.md").write_text(to_markdown(result), encoding="utf-8")
    print(json.dumps({k: result.get(k) for k in ("status", "labelled_items", "sample_size", "problems", "detail")}, ensure_ascii=False, indent=2))
    return EXIT[result["status"]]


if __name__ == "__main__":
    sys.exit(main())
