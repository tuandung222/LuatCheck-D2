"""Recompute summaries from native artifacts and completed human labels; no inference."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np


FIELDS = ["task_id", "seed", "mode", "reviewer", "task_correct", "total_claims", "unsupported_claims", "failure_modes", "notes"]
FAILURE_MODES = {"retrieval_miss", "wrong_provision", "quantity_negation", "unsupported_claim",
                 "over_refusal", "wrong_clarification", "parse_error", "deadline", "backend_error", "other"}


def read_runs(run_dir):
    root = Path(run_dir)
    manifest = json.loads((root / "manifest.json").read_text())
    if manifest.get("schema") != "luatcheck.native.d2.v1" or manifest.get("status") != "collected_pending_human_scoring":
        raise ValueError("Only a complete native collection can be scored.")
    if manifest.get("runs_sha256") != hashlib.sha256((root / "runs.jsonl").read_bytes()).hexdigest():
        raise ValueError("Run artifact hash does not match the collection manifest.")
    rows = [json.loads(line) for line in (root / "runs.jsonl").read_text().splitlines() if line.strip()]
    expected = {(t, seed, mode) for t in manifest["task_ids"] for seed in manifest["seeds"] for mode in manifest["modes"]}
    keys = [(r["task_id"], r["seed"], r["mode"]) for r in rows]
    if len(keys) != len(set(keys)) or set(keys) != expected:
        raise ValueError("Run coverage has duplicates, extras or missing trials.")
    backend = manifest.get("model", {}).get("provider", "ollama")
    for row in rows:
        calls = row.get("ledger", {}).get("llm_calls", [])
        if len(calls) != row["native_calls"] or any(c.get("backend") != backend for c in calls):
            raise ValueError("Native call ledger does not match the trial.")
        if sum(c.get("outcome") == "success" for c in calls) != row["successful_native_calls"]:
            raise ValueError("Native success count does not match the ledger.")
        if row["terminal_status"] != row["ledger"]["terminal_status"] or row["ledger"].get("final_output", {}).get("from_cache"):
            raise ValueError("Trial status mismatch or cached output is ineligible.")
        if row["terminal_status"] == "answered" and row.get("successful_native_calls", 0) < 1:
            raise ValueError("An answer without native call evidence is ineligible.")
    return manifest, rows


def create_template(run_dir, destination):
    _, rows = read_runs(run_dir)
    with Path(destination).open("x", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row[k] for k in ["task_id", "seed", "mode"]})


def score(run_dir, labels_file):
    manifest, rows = read_runs(run_dir)
    with Path(labels_file).open(newline="") as stream:
        labels = list(csv.DictReader(stream))
    label_keys = [(r["task_id"], int(r["seed"]), r["mode"]) for r in labels]
    run_keys = {(r["task_id"], r["seed"], r["mode"]) for r in rows}
    if len(label_keys) != len(set(label_keys)) or set(label_keys) != run_keys:
        raise ValueError("Human labels must cover every trial exactly once.")
    by_key = {}
    for key, label in zip(label_keys, labels):
        if not label.get("reviewer", "").strip() or label.get("task_correct") not in {"0", "1"}:
            raise ValueError("Reviewer and binary task_correct are required; missing labels never become zero.")
        total, unsupported = int(label["total_claims"]), int(label["unsupported_claims"])
        if total < 0 or not 0 <= unsupported <= total:
            raise ValueError("Invalid human claim counts.")
        failures = {v.strip() for v in label.get("failure_modes", "").split(";") if v.strip()}
        if failures - FAILURE_MODES:
            raise ValueError("Unknown human failure-mode tag.")
        by_key[key] = {"correct": int(label["task_correct"]), "total": total, "unsupported": unsupported,
                       "failures": failures}
    summary = {"phase": manifest["phase"], "results": {},
               "collection_manifest_sha256": hashlib.sha256((Path(run_dir)/"manifest.json").read_bytes()).hexdigest(),
               "human_labels_sha256": hashlib.sha256(Path(labels_file).read_bytes()).hexdigest(),
               "report_eligible": (manifest["phase"] == "main" and manifest.get("tokens_complete", False)
                                   and set(manifest["modes"]) == {"off", "l1_on"}
                                   and len(manifest["task_ids"]) >= 10 and len(manifest["seeds"]) >= 3),
               "GPU_active_hours": None,
               "note": "Human-reviewed outcomes; automated lexical proxies remain separate. Pilot outputs are never main results."}
    for mode in manifest["modes"]:
        subset = [r for r in rows if r["mode"] == mode]
        gold_subset = [r for r in subset if r.get("gold_article_ids")]
        lexical_subset = [r["lexical_unsupported_proxy"] for r in subset if r.get("lexical_unsupported_proxy") is not None]
        for row in subset:
            label = by_key[row["task_id"], row["seed"], mode]
            if row.get("system_error") and label["correct"]:
                raise ValueError("Execution errors cannot be labelled as successful tasks.")
        per_seed = [np.mean([by_key[r["task_id"], seed, mode]["correct"] for r in subset if r["seed"] == seed])
                    for seed in manifest["seeds"]]
        total_claims = sum(by_key[r["task_id"], r["seed"], mode]["total"] for r in subset)
        unsupported = sum(by_key[r["task_id"], r["seed"], mode]["unsupported"] for r in subset)
        summary["results"][mode] = {
            "trials": len(subset), "system_errors": sum(r["system_error"] for r in subset),
            "human_task_success_mean": float(np.mean(per_seed)),
            "human_task_success_std_across_seeds": float(np.std(per_seed, ddof=1)) if len(per_seed) > 1 else None,
            "human_claims_total": total_claims, "human_unsupported_claims": unsupported,
            "human_failure_counts_overlapping": {tag: sum(tag in by_key[r["task_id"], r["seed"], mode]["failures"]
                                                          for r in subset) for tag in sorted(FAILURE_MODES)},
            "execution_error_counts": {kind: sum(r.get("error_kind") == kind for r in subset)
                                        for kind in ["backend_error", "model_output_error", "wall_timeout"]},
            "human_unsupported_rate": unsupported/total_claims if total_claims else None,
            "coverage": sum(r["terminal_status"] == "answered" for r in subset)/len(subset),
            "latency_p50_ms": float(np.percentile([r["wall_ms"] for r in subset], 50)),
            "latency_p95_ms": float(np.percentile([r["wall_ms"] for r in subset], 95)),
            "input_tokens": sum(r["input_tokens"] for r in subset) if all(r["input_tokens"] is not None for r in subset) else None,
            "output_tokens": sum(r["output_tokens"] for r in subset) if all(r["output_tokens"] is not None for r in subset) else None,
            "input_tokens_per_task_mean": float(np.mean([r["input_tokens"] for r in subset])) if all(r["input_tokens"] is not None for r in subset) else None,
            "output_tokens_per_task_mean": float(np.mean([r["output_tokens"] for r in subset])) if all(r["output_tokens"] is not None for r in subset) else None,
            "task_wall_hours_sum": sum(r["wall_ms"] for r in subset)/3600000,
            "task_wall_seconds_mean": float(np.mean([r["wall_ms"] for r in subset]))/1000,
            "gold_article_trials": len(gold_subset),
            "retrieval_recall5_mean": float(np.mean([r["retrieval"]["Recall@5"] for r in gold_subset])) if gold_subset else None,
            "retrieval_hit5_mean": float(np.mean([r["retrieval"]["Hit@5"] for r in gold_subset])) if gold_subset else None,
            "citation_precision_mean": float(np.mean([r["citation"]["citation_precision"] for r in gold_subset])) if gold_subset else None,
            "citation_recall_mean": float(np.mean([r["citation"]["citation_recall"] for r in gold_subset])) if gold_subset else None,
            "lexical_unsupported_proxy_answered_only": float(np.mean(lexical_subset)) if lexical_subset else None,
            "human_success_by_expected_behavior": {
                behavior: {"trials": sum(r["expected_behavior"] == behavior for r in subset),
                           "correct": sum(by_key[r["task_id"], r["seed"], mode]["correct"] for r in subset if r["expected_behavior"] == behavior)}
                for behavior in ["answer", "clarify", "refuse"]},
        }
    if set(manifest["modes"]) == {"off", "l1_on"}:
        differences = [np.mean([by_key[t, s, "l1_on"]["correct"] - by_key[t, s, "off"]["correct"] for s in manifest["seeds"]])
                       for t in manifest["task_ids"]]
        summary["paired_tasks"] = {"ON_wins": sum(x > 0 for x in differences),
                                   "ties": sum(x == 0 for x in differences),
                                   "OFF_wins": sum(x < 0 for x in differences),
                                   "unit": "Distinct task, averaging repeated seeds; no independence/significance claim."}
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--labels", required=True)
    parser.add_argument("--create-template", action="store_true")
    parser.add_argument("--output")
    args = parser.parse_args()
    if args.create_template:
        create_template(args.run_dir, args.labels)
    else:
        if not args.output:
            parser.error("--output is required for scoring")
        result = score(args.run_dir, args.labels)
        with Path(args.output).open("x") as stream:
            json.dump(result, stream, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
