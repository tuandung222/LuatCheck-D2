"""Aggregate real LLM judgments and prepare an unlabelled human audit sample."""
import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
from pathlib import Path

from evaluation.judge_gateway import sha, validate


def analyze(judge_dir, blind_dir, output, recovery_dir=None):
    root, blind, destination = Path(judge_dir), Path(blind_dir), Path(output)
    manifest = json.loads((root / "manifest.json").read_text())
    if manifest["status"] != "collected_pending_human_validation" or manifest["phase"] != "main":
        raise ValueError("A complete main judge collection is required")
    if sha(root / "judgments.jsonl") != manifest["judgments_sha256"]:
        raise ValueError("Judgment hash mismatch")
    for name, digest in manifest["input_sha256"].items():
        if sha(root / name) != digest:
            raise ValueError("Frozen judge input/code/config mismatch")
    for name, digest in manifest["attempts_sha256"].items():
        if sha(root / "attempts" / name) != digest:
            raise ValueError("Judge API attempt hash mismatch")
    packets = {r["review_id"]: r for r in json.loads((root / "input-judge_packets.json").read_text())}
    original = json.loads((blind / "manifest.json").read_text())
    for name, digest in original["files_sha256"].items():
        if sha(blind / name) != digest:
            raise ValueError("Original blind-review package hash mismatch")
    if manifest["source_runs_sha256"] != original["runs_sha256"] or sha(blind / "judge_packets.json") != sha(root / "input-judge_packets.json"):
        raise ValueError("Judge inputs do not match the original native batch")
    mapping = {r["review_id"]: r for r in json.loads((blind / "private_mapping.json").read_text())}
    rows = [json.loads(s) for s in (root / "judgments.jsonl").read_text().splitlines()]
    ids = [r["review_id"] for r in rows]
    if len(ids) != len(set(ids)) or set(ids) != set(manifest["expected_review_ids"]) or set(ids) != set(mapping):
        raise ValueError("Missing, duplicate or extra main judgments")
    recovery_manifest = None
    parser_overrides = []
    attempt_roots = [root]
    def revalidate(row, base):
        if row["status"] == "valid":
            return row
        for name in row["attempts"]:
            path = base / "attempts" / name
            record = json.loads(path.read_text())
            if record.get("http_status") != 200 or record.get("finish_reason") != "stop":
                continue
            try:
                content = (record["assembled_content"] if "assembled_content" in record else
                           json.loads(record["raw_body"])["choices"][0]["message"]["content"])
                judgment = validate(json.loads(content), packets[row["review_id"]])
            except (ValueError, KeyError, TypeError):
                continue
            parser_overrides.append({"review_id": row["review_id"], "attempt_path": str(path),
                                     "attempt_sha256": sha(path), "original_status": record["status"],
                                     "original_error": record.get("error"), "revalidated_status": "valid",
                                     "note": "Parser correction: a known article ID with null source_quote is permitted for not_established claims by the frozen rubric. No model scores, quotes or labels edited."})
            return {**row, "status": "valid", "judgment": judgment, "parser_revalidated": True}
        return row
    for row in rows:
        row["judgment_origin"] = "main"
    if recovery_dir:
        recovery = Path(recovery_dir)
        recovery_manifest = json.loads((recovery / "manifest.json").read_text())
        if (recovery_manifest["status"] != "collected_pending_human_validation"
            or recovery_manifest["phase"] != "schema_failure_recovery"
            or recovery_manifest["initial_judgments_sha256"] != manifest["judgments_sha256"]):
            raise ValueError("Recovery provenance mismatch")
        if sha(recovery / "judgments.jsonl") != recovery_manifest["judgments_sha256"]:
            raise ValueError("Recovery judgment hash mismatch")
        for name, digest in recovery_manifest["input_sha256"].items():
            if sha(recovery / name) != digest:
                raise ValueError("Recovery frozen input mismatch")
        for name, digest in recovery_manifest["attempts_sha256"].items():
            if sha(recovery / "attempts" / name) != digest:
                raise ValueError("Recovery attempt hash mismatch")
        for name in ("input-judge_packets.json", "input-SEMANTIC_JUDGING.md", "judge_prompt.txt"):
            if sha(recovery / name) != sha(root / name):
                raise ValueError("Recovery changed semantic inputs/prompts")
        if any(recovery_manifest["config"][k] != manifest["config"][k]
               for k in ("base_url", "model", "thinking", "reasoning_effort")):
            raise ValueError("Recovery changed model or semantic settings")
        recovery_rows = [json.loads(s) for s in (recovery / "judgments.jsonl").read_text().splitlines()]
        recovered = {r["review_id"]: r for r in recovery_rows}
        invalid_ids = {r["review_id"] for r in rows if r["status"] != "valid"}
        if len(recovery_rows) != len(recovered) or set(recovered) != invalid_ids:
            raise ValueError("Recovery must cover all and only initial invalid judgments")
        rows = [{**revalidate(recovered[r["review_id"]], recovery), "judgment_origin": "recovery"}
                if r["review_id"] in recovered else r for r in rows]
        attempt_roots.append(recovery)
    details = []
    attempts = [json.loads(p.read_text()) for base in attempt_roots
                for p in sorted((base / "attempts").glob("*.json"))]
    for row in rows:
        packet, meta = packets[row["review_id"]], mapping[row["review_id"]]
        judgment = row["judgment"]
        if row["status"] == "valid":
            validate(judgment, packet)
        if row["status"] != "valid" or not judgment["judgeable"]:
            success = False if meta["system_error"] else None
        else:
            success = (not meta["system_error"] and judgment["behaviour_appropriate"]
                       and judgment["correctness"] == 2 and judgment["completeness"] == 2
                       and all(c["support"] == "supported" for c in judgment["claims"]))
        details.append({**meta, "valid_judgment": row["status"] == "valid",
                        "judgment_origin": row["judgment_origin"],
                        "judgeable": judgment["judgeable"] if row["status"] == "valid" else None,
                        "llm_task_success_estimate": success, "judgment": judgment})
    summary = {"evaluation_type": "LLM-judge estimates, not human-validated correctness",
               "judge_config": manifest["config"], "native_runs_sha256": manifest["source_runs_sha256"],
               "analysis_source_sha256": sha(Path(__file__)),
               "validation_source_sha256": sha(Path("evaluation/judge_gateway.py")),
               "parser_revalidation_overrides": parser_overrides,
               "judgments_sha256": manifest["judgments_sha256"], "trials": len(rows),
               "human_judge_agreement": None, "human_cohens_kappa": None,
               "human_labels_received": False, "modes": {}, "api_usage": {}}
    summary["recovery"] = ({"manifest_sha256": sha(Path(recovery_dir) / "manifest.json"),
                            "judgments_sha256": recovery_manifest["judgments_sha256"],
                            "trials": recovery_manifest["collected"],
                            "valid": sum(r["status"] == "valid" for r in rows if r["judgment_origin"] == "recovery"),
                            "original_collector_valid": recovery_manifest["valid"],
                            "config": recovery_manifest["config"],
                            "selection": recovery_manifest["selection_rule"],
                            "note": recovery_manifest["protocol_development_note"]}
                           if recovery_manifest else None)
    for mode in sorted({r["mode"] for r in details}):
        subset = [r for r in details if r["mode"] == mode]
        scored = [r for r in subset if r["valid_judgment"] and r["judgeable"]]
        known = [r for r in subset if r["llm_task_success_estimate"] is not None]
        successes = sum(r["llm_task_success_estimate"] is True for r in subset)
        unknown = len(subset) - len(known)
        claims = [c for r in scored for c in r["judgment"]["claims"]]
        supported = sum(c["support"] == "supported" for c in claims)
        summary["modes"][mode] = {
            "trials": len(subset), "valid_judgments": sum(r["valid_judgment"] for r in subset),
            "judgeable_judgments": len(scored), "unknown_task_outcomes": unknown,
            "success_count_estimate": successes, "known_outcome_denominator": len(known),
            "task_success_rate_estimate_known": successes / len(known) if known else None,
            "success_rate_lower_bound_all_trials": successes / len(subset),
            "success_rate_upper_bound_all_trials": (successes + unknown) / len(subset),
            "behaviour_appropriate_count": sum(r["judgment"]["behaviour_appropriate"] for r in scored),
            "correctness_0_1_2": dict(Counter(str(r["judgment"]["correctness"]) for r in scored)),
            "completeness_0_1_2": dict(Counter(str(r["judgment"]["completeness"]) for r in scored)),
            "factual_claims": len(claims), "supported_claims": supported,
            "contradicted_claims": sum(c["support"] == "contradicted" for c in claims),
            "not_established_claims": sum(c["support"] == "not_established" for c in claims),
            "claim_faithfulness_estimate": supported / len(claims) if claims else None,
            "unsupported_claim_rate_estimate": (len(claims) - supported) / len(claims) if claims else None,
            "claim_rate_note": "Micro-average over factual claims in valid judgeable outputs, including any claims in refusals/clarifications; zero-claim outputs do not create artificial perfect faithfulness.",
            "reference_issues": [{"review_id": r["review_id"], "issue": r["judgment"]["reference_issue"]}
                                 for r in subset if r["valid_judgment"] and not r["judgeable"]]}
    usage = [a.get("usage") or {} for a in attempts]
    complete = all(type(u.get(k)) is int for u in usage for k in ("prompt_tokens", "completion_tokens"))
    costs = [u.get("cost") for u in usage]
    metered = [u for u in usage if all(type(u.get(k)) is int for k in ("prompt_tokens", "completion_tokens"))]
    known_costs = [c for c in costs if type(c) in (int, float)]
    header_costs, cost_conflicts = [], []
    for attempt in attempts:
        headers = {k.lower(): v for k, v in attempt.get("response_headers", {}).items()}
        try:
            header_cost = float(headers["x-litellm-response-cost"])
        except (KeyError, TypeError, ValueError):
            continue
        header_costs.append(header_cost)
        body_cost = (attempt.get("usage") or {}).get("cost")
        if type(body_cost) in (int, float) and abs(body_cost - header_cost) > 1e-10:
            cost_conflicts.append({"review_id": attempt["review_id"], "attempt": attempt["attempt"],
                                   "stream": attempt["request"]["stream"],
                                   "body_usage_cost": body_cost, "header_response_cost": header_cost})
    anomalies = []
    for attempt in attempts:
        u = attempt.get("usage") or {}
        reasoning = (u.get("completion_tokens_details") or {}).get("reasoning_tokens")
        completion = u.get("completion_tokens")
        if type(reasoning) is int and type(completion) is int and reasoning > completion:
            anomalies.append({"review_id": attempt["review_id"], "attempt": attempt["attempt"],
                              "reported_completion_tokens": completion, "reported_reasoning_tokens": reasoning,
                              "issue": "Reasoning detail exceeds reported completion_tokens; provider counts are retained without correction."})
    summary["api_usage"] = {
        "attempts_including_failed": len(attempts), "valid_attempts": sum(a["status"] == "valid" for a in attempts),
        "prompt_tokens": sum(u["prompt_tokens"] for u in usage) if complete else None,
        "reported_completion_tokens": sum(u["completion_tokens"] for u in usage) if complete else None,
        "usage_complete": complete,
        "usage_consistency_anomalies": anomalies,
        "metered_attempts": len(metered), "missing_usage_attempts": len(usage) - len(metered),
        "observed_prompt_tokens_subtotal": sum(u["prompt_tokens"] for u in metered),
        "observed_completion_tokens_subtotal": sum(u["completion_tokens"] for u in metered),
        "gateway_reported_cost_usd": sum(costs) if all(type(c) in (int, float) for c in costs) else None,
        "gateway_reported_cost_subtotal_usd": sum(known_costs),
        "body_usage_cost_subtotal_usd": sum(known_costs),
        "header_cost_subtotal_usd": sum(header_costs),
        "header_cost_attempts": len(header_costs),
        "body_header_cost_conflicts": cost_conflicts,
        "attempts_with_reported_cost": len(known_costs), "missing_cost_attempts": len(costs) - len(known_costs),
        "actual_invoiced_charge_usd": None,
        "returned_model_ids": dict(Counter(str(a.get("returned_model")) for a in attempts)),
        "cost_note": "Gateway usage.cost, including retained failed attempts when reported; not an independently verified invoice. Missing usage or cost is unknown, not zero."}
    # At least one reproducibly chosen item per nonempty mode/category/outcome stratum.
    groups = defaultdict(list)
    eligible = [r for r in details if r["valid_judgment"] and r["judgeable"]]
    unresolved = [r for r in details if not r["valid_judgment"] or not r["judgeable"]]
    for row in eligible:
        outcome = "unknown" if row["llm_task_success_estimate"] is None else str(row["llm_task_success_estimate"])
        groups[(row["mode"], row["category"], outcome)].append(row)
    def order(row):
        return hashlib.sha256(("LuatCheck-human-audit-20261022:" + row["review_id"]).encode()).hexdigest()
    selected = []
    for key in sorted(groups):
        selected.append(sorted(groups[key], key=order)[0])
    selected_ids = {r["review_id"] for r in selected}
    for row in sorted(eligible, key=order):
        if len(selected) >= max(12, len(groups)):
            break
        if row["review_id"] not in selected_ids:
            selected.append(row)
            selected_ids.add(row["review_id"])
    destination.mkdir(parents=True, exist_ok=False)
    summary["human_audit_sample"] = {"count": len(selected), "selected_review_ids": sorted(selected_ids),
        "eligible_population": len(eligible),
        "method": "One hash-selected valid judgeable record per nonempty mode/category/judge-outcome stratum; hash-ordered fill to at least 12. Reliability sample excludes missing LLM judgments, which receive a separate targeted review. Selected before any human labels; no human labels generated."}
    summary["targeted_unresolved_review"] = {"count": len(unresolved), "review_ids": sorted(r["review_id"] for r in unresolved),
        "note": "Separate targeted review, excluded from the fixed reliability sample; no valid LLM estimate exists for these outputs."}
    (destination / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    (destination / "private-judge-details.json").write_text(json.dumps(details, ensure_ascii=False, indent=2) + "\n")
    human = destination / "human-audit"
    human.mkdir()
    (human / "packets.json").write_text(json.dumps([packets[i] for i in sorted(selected_ids)], ensure_ascii=False, indent=2) + "\n")
    with (human / "labels.csv").open("x", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["review_id", "reviewer", "judgeable", "behaviour_appropriate", "correctness", "completeness", "total_claims", "unsupported_claims", "notes"])
        for i in sorted(selected_ids):
            writer.writerow([i, "", "", "", "", "", "", "", ""])
    (human / "README.md").write_text("# Human audit — labels blank\n\nRead packets.json with the frozen SEMANTIC_JUDGING.md. Judge independently without mode/seed/model or the LLM judgments. Fill labels.csv with actual reviewer identity and labels; record source disagreements. This sample has been stratified using private mode/category/judge outcomes, so its agreement is a sample diagnostic, not population certification. No human labels have been generated.\n")
    (human / "SEMANTIC_JUDGING.md").write_text((root / "input-SEMANTIC_JUDGING.md").read_text())
    (human / "unresolved-packets.json").write_text(json.dumps([packets[r["review_id"]] for r in sorted(unresolved, key=lambda r: r["review_id"])], ensure_ascii=False, indent=2) + "\n")
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--judge-dir", required=True)
    parser.add_argument("--blind-dir", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--recovery-dir")
    args = parser.parse_args()
    value = analyze(args.judge_dir, args.blind_dir, args.output, args.recovery_dir)
    print(json.dumps({k: value[k] for k in ("trials", "modes", "api_usage", "human_audit_sample")}, ensure_ascii=False, indent=2))
