"""Audit actual API artifacts and summary arithmetic, without assigning labels."""
import csv
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from evaluation.judge_gateway import validate

RUN = ROOT / "evaluation/runs/deepseek-judge-main-v1"
ANALYSIS = RUN / "analysis-final"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    manifest = json.loads((RUN / "manifest.json").read_text())
    assert manifest["status"] == "collected_pending_human_validation"
    assert digest(RUN / "judgments.jsonl") == manifest["judgments_sha256"]
    for name, expected in manifest["input_sha256"].items():
        assert digest(RUN / name) == expected, name
    for name, expected in manifest["attempts_sha256"].items():
        assert digest(RUN / "attempts" / name) == expected, name
    packets = {p["review_id"]: p for p in json.loads((RUN / "input-judge_packets.json").read_text())}
    rows = [json.loads(s) for s in (RUN / "judgments.jsonl").read_text().splitlines()]
    assert len(rows) == len({r["review_id"] for r in rows}) == 60
    assert {r["review_id"] for r in rows} == set(packets)
    attempts = []
    cost_conflicts = []
    for row in rows:
        packet = packets[row["review_id"]]
        if row["status"] == "valid":
            validate(row["judgment"], packet)
        valid_records = []
        for name in row["attempts"]:
            record = json.loads((RUN / "attempts" / name).read_text())
            attempts.append(record)
            sent = record["request"]["messages"][1]["content"].split("\n", 1)[1]
            assert json.loads(sent) == packet
            assert not (set(packet) & {"mode", "seed", "model", "task_id", "verified"})
            assert record["request"]["model"] == manifest["config"]["model"]
            if record.get("http_status") == 200:
                raw = json.loads(record["raw_body"])
                assert raw["usage"] == record["usage"]
                assert raw["model"] == record["returned_model"]
                assert raw["model"] in manifest["config"]["allowed_returned_models"]
                headers = {k.lower(): v for k, v in record["response_headers"].items()}
                if "x-litellm-response-cost" in headers and record["usage"].get("cost") is not None:
                    if abs(float(headers["x-litellm-response-cost"]) - record["usage"]["cost"]) > 1e-10:
                        cost_conflicts.append({"review_id": row["review_id"], "attempt": record["attempt"],
                                               "header_cost": float(headers["x-litellm-response-cost"]),
                                               "body_usage_cost": record["usage"]["cost"]})
                if record["status"] == "valid":
                    valid_records.append(json.loads(raw["choices"][0]["message"]["content"]))
        if row["status"] == "valid":
            assert valid_records[-1] == row["judgment"]
    summary = json.loads((ANALYSIS / "summary.json").read_text())
    details = json.loads((ANALYSIS / "private-judge-details.json").read_text())
    final_rows = {r["review_id"]: r for r in rows}
    recovery_verified = 0
    if summary.get("recovery"):
        recovery = ROOT / "evaluation/runs/deepseek-judge-recovery-v1"
        rm = json.loads((recovery / "manifest.json").read_text())
        assert rm["initial_judgments_sha256"] == manifest["judgments_sha256"]
        assert digest(recovery / "manifest.json") == summary["recovery"]["manifest_sha256"]
        assert digest(recovery / "judgments.jsonl") == rm["judgments_sha256"]
        for name, expected in rm["input_sha256"].items():
            assert digest(recovery / name) == expected
        for name, expected in rm["attempts_sha256"].items():
            assert digest(recovery / "attempts" / name) == expected
        recovered = [json.loads(s) for s in (recovery / "judgments.jsonl").read_text().splitlines()]
        assert {r["review_id"] for r in recovered} == {r["review_id"] for r in rows if r["status"] != "valid"}
        for row in recovered:
            final_rows[row["review_id"]] = row
            for name in row["attempts"]:
                record = json.loads((recovery / "attempts" / name).read_text())
                attempts.append(record)
                sent = record["request"]["messages"][1]["content"].split("\n", 1)[1]
                assert json.loads(sent) == packets[row["review_id"]]
                chunks = []
                for line in record.get("raw_body", "").splitlines():
                    if line.startswith("data:") and line[5:].strip() != "[DONE]":
                        chunks.append(json.loads(line[5:].strip()))
                assert chunks == record["stream_chunks"]
                content = "".join(c.get("delta", {}).get("content") or "" for chunk in chunks for c in chunk.get("choices", []))
                if row["status"] == "valid":
                    assert json.loads(content) == row["judgment"]
                    validate(row["judgment"], packets[row["review_id"]])
                    assert record["finish_reason"] == "stop" and record["done_marker_received"]
                    assert next(c["usage"] for c in reversed(chunks) if c.get("usage") is not None) == record["usage"]
                    recovery_verified += 1
    overrides = {r["review_id"]: r for r in summary.get("parser_revalidation_overrides", [])}
    for detail in details:
        if detail["review_id"] in overrides:
            override = overrides[detail["review_id"]]
            path = Path(override["attempt_path"])
            if not path.is_absolute():
                path = ROOT / path
            assert digest(path) == override["attempt_sha256"]
            record = json.loads(path.read_text())
            assert record["http_status"] == 200 and record["finish_reason"] == "stop"
            raw = (record["assembled_content"] if "assembled_content" in record else
                   json.loads(record["raw_body"])["choices"][0]["message"]["content"])
            assert detail["judgment"] == json.loads(raw)
            validate(detail["judgment"], packets[detail["review_id"]])
        else:
            assert detail["judgment"] == final_rows[detail["review_id"]]["judgment"]
    for mode, metric in summary["modes"].items():
        sub = [d for d in details if d["mode"] == mode]
        known = [d for d in sub if d["llm_task_success_estimate"] is not None]
        assert metric["trials"] == len(sub) == 30
        assert metric["known_outcome_denominator"] == len(known)
        successes = 0
        for detail in sub:
            judgment = detail["judgment"]
            if detail["system_error"]:
                expected = False
            elif not detail["valid_judgment"] or not detail["judgeable"]:
                expected = None
            else:
                expected = (judgment["correctness"] == judgment["completeness"] == 2
                            and judgment["behaviour_appropriate"]
                            and all(c["support"] == "supported" for c in judgment["claims"]))
            assert detail["llm_task_success_estimate"] is expected
            successes += expected is True
        assert metric["success_count_estimate"] == successes
        claims = [c for d in sub if d["valid_judgment"] and d["judgeable"] for c in d["judgment"]["claims"]]
        assert metric["factual_claims"] == len(claims)
        assert metric["supported_claims"] == sum(c["support"] == "supported" for c in claims)
    usage = summary["api_usage"]
    assert usage["attempts_including_failed"] == len(attempts)
    if usage["usage_complete"]:
        assert usage["prompt_tokens"] == sum(a["usage"]["prompt_tokens"] for a in attempts)
        assert usage["reported_completion_tokens"] == sum(a["usage"]["completion_tokens"] for a in attempts)
    metered = [a["usage"] for a in attempts if a.get("usage") and all(type(a["usage"].get(k)) is int for k in ("prompt_tokens", "completion_tokens"))]
    assert usage["observed_prompt_tokens_subtotal"] == sum(u["prompt_tokens"] for u in metered)
    assert usage["observed_completion_tokens_subtotal"] == sum(u["completion_tokens"] for u in metered)
    labels = list(csv.DictReader((ANALYSIS / "human-audit/labels.csv").open()))
    assert len(labels) >= 12
    assert all(not value for row in labels for field, value in row.items() if field != "review_id")
    assert summary["human_judge_agreement"] is None and summary["human_cohens_kappa"] is None
    assert summary["human_labels_received"] is False
    receipt = {"status": "artifact_integrity_passed_with_provider_accounting_anomalies", "judge_trials": len(rows), "api_attempts": len(attempts),
               "provider_nonstream_cost_fields_consistent": not cost_conflicts,
               "provider_nonstream_cost_conflicts": cost_conflicts,
               "provider_usage_consistency_anomaly_count": len(usage["usage_consistency_anomalies"]),
               "valid_streamed_recovery_judgments_verified": recovery_verified,
               "unaltered_raw_judgments_restored_by_parser_correction": len(overrides),
               "judgments_sha256": digest(RUN / "judgments.jsonl"),
               "human_audit_sample": len(labels), "human_labels_present": False,
               "checks": ["all frozen input and attempt hashes", "60 unique blinded packets", "actual API body-to-judgment match",
                          "raw usage/body retention with cost disagreements explicitly flagged", "SSE chunk-to-judgment replay if recovery used", "strict success and claim-count arithmetic", "blank human audit labels"],
               "not_validated": ["semantic judge reliability", "human/expert correctness", "immutable upstream model revision", "actual invoice"]}
    Path(__file__).with_name("verification.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
