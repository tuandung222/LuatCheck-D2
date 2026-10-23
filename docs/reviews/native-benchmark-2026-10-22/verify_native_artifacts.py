"""Independent arithmetic/provenance checks of the completed native batch."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RUN = ROOT / "evaluation/runs/bll2019-main-v2"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    manifest = json.loads((RUN / "manifest.json").read_text())
    assert manifest["status"] == "collected_pending_human_scoring"
    assert digest(RUN / "runs.jsonl") == manifest["runs_sha256"]
    for name, expected in manifest["sources"]["files_sha256"].items():
        assert digest(RUN / "source_snapshot" / name) == expected, name
    rows = [json.loads(s) for s in (RUN / "runs.jsonl").read_text().splitlines()]
    keys = [(r["task_id"], r["seed"], r["mode"]) for r in rows]
    expected = {(t, s, m) for t in manifest["task_ids"] for s in manifest["seeds"] for m in manifest["modes"]}
    assert len(keys) == len(set(keys)) and set(keys) == expected
    cfg = manifest["config"]["model"]
    call_count = 0
    for row in rows:
        ledger = row["ledger"]
        gold = set(row["gold_article_ids"])
        retrieved = list(dict.fromkeys(ledger["retrieved_article_ids"]))
        for k in (1, 3, 5):
            overlap = len(gold & set(retrieved[:k]))
            recall = overlap / len(gold) if gold else 0.0
            hit = float(overlap > 0)
            assert abs(row["retrieval"][f"Recall@{k}"] - recall) < 1e-12
            assert abs(row["retrieval"][f"Hit@{k}"] - hit) < 1e-12
        rank = next((i for i, article in enumerate(retrieved, 1) if article in gold), None)
        # Collector records MRR/citation fractions to four decimal places.
        assert abs(row["retrieval"]["MRR"] - (1/rank if rank else 0.0)) <= 0.00005
        final = ledger["final_output"]
        cited = {c["article_id"] for c in final.get("citations", [])}
        precision = len(cited & gold) / len(cited) if cited else 0.0
        recall = len(cited & gold) / len(gold) if gold else 0.0
        if gold:
            assert abs(row["citation"]["citation_precision"] - precision) <= 0.00005
            assert abs(row["citation"]["citation_recall"] - recall) <= 0.00005
        calls = ledger["llm_calls"]
        assert calls, "This selected batch must have native invocation evidence for every trial"
        assert not final.get("from_cache")
        for call in calls:
            assert call["backend"] == "ollama"
            payload = {"model": cfg["name"], "messages": call["request_messages"], "stream": False,
                       "format": "json", "options": {"temperature": cfg["temperature"], "top_p": 0.9,
                       "num_predict": cfg["max_output_tokens"], "num_ctx": cfg["context_tokens"],
                       "seed": row["seed"]}, "keep_alive": "10m"}
            actual = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
            assert actual == call["request_sha256"]
            native = call.get("native_response")
            if native is not None:
                assert call["input_tokens"] == native.get("prompt_eval_count")
                assert call["output_tokens"] == native.get("eval_count")
            call_count += 1
        if row["token_usage_complete"]:
            assert row["input_tokens"] == sum(c["input_tokens"] for c in calls)
            assert row["output_tokens"] == sum(c["output_tokens"] for c in calls)
        else:
            assert row["input_tokens"] is None and row["output_tokens"] is None
        assert row["wall_ms"] > 0
    receipt = {"status": "passed", "trials": len(rows), "native_calls": call_count,
               "runs_sha256": digest(RUN / "runs.jsonl"),
               "checks": ["full Cartesian coverage", "all snapshot file hashes", "retrieval arithmetic",
                          "citation-ID arithmetic", "native request hashes", "raw native usage", "no answer-cache hits"],
               "semantic_correctness_validated": False,
               "undefined_metrics": "Citation-ID fractions on empty-gold foreign-scope trials are inapplicable; frozen raw rows retain a legacy convention. They are excluded from report aggregates. MRR uses the full ordered unique tool trajectory; Recall/Hit@5 use its first five IDs.",
               "note": "Arithmetic and recorded provenance checks; not backend attestation, legal expert review or human labels. The manifest model.inference_executed=false is the preflight snapshot, not a count of collection invocations."}
    output = Path(__file__).with_name("artifact-verification.json")
    output.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
