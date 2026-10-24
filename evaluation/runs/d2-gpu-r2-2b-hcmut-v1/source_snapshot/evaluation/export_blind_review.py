"""Export source-grounded review packets; never generate evaluation labels."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

from evaluation.score_reviewed_runs import read_runs


def export(run_dir, output):
    root = Path(run_dir)
    manifest, rows = read_runs(root)  # Reject incomplete or changed collections.
    snapshot = root / "source_snapshot"
    task_path = next(p for p in manifest["sources"]["files_sha256"]
                     if p.endswith("/tasks.json"))
    corpus_path = manifest["config"]["retrieval"]["corpus_path"]
    for path in (task_path, corpus_path):
        actual = hashlib.sha256((snapshot / path).read_bytes()).hexdigest()
        if actual != manifest["sources"]["files_sha256"][path]:
            raise ValueError("Frozen review source hash mismatch: " + path)
    tasks = {t["task_id"]: t for t in json.loads((snapshot / task_path).read_text())}
    corpus = {a["article_id"]: a for a in json.loads((snapshot / corpus_path).read_text())}
    protocol = Path(task_path).parent / "SEMANTIC_JUDGING.md"
    if not protocol.is_file():
        raise ValueError("Semantic judging protocol is required")
    packets, mapping = [], []
    for row in rows:
        task = tasks[row["task_id"]]
        if task["question"] != row["ledger"]["original_query"] or task["expected_behavior"] != row["expected_behavior"]:
            raise ValueError("Frozen task does not match collected question/behaviour")
        key = json.dumps([manifest["runs_sha256"], row["task_id"], row["seed"], row["mode"]])
        review_id = hashlib.sha256(key.encode()).hexdigest()[:24]
        final = row["ledger"].get("final_output") or {}
        answer_field = {"answered": "content", "clarified": "question",
                        "refused": "reason", "error": "reason"}[row["terminal_status"]]
        citations = [{k: c[k] for k in ("article_id", "exact_quote") if k in c}
                     for c in final.get("citations", [])]
        ids = set(task["ground_truth_article_ids"]) | set(row["ledger"]["retrieved_article_ids"])
        ids |= {c["article_id"] for c in citations if "article_id" in c}
        packets.append({
            "review_id": review_id, "question": task["question"],
            "scope": task["scope"], "expected_behavior": task["expected_behavior"],
            "reference_answer": task["expected_answer"],
            "reference_evidence": task.get("reference_evidence", []),
            "candidate_behavior": row["terminal_status"],
            "candidate_answer": final.get(answer_field, ""), "candidate_citations": citations,
            "source_articles": [corpus[i] for i in sorted(ids) if i in corpus],
            "unknown_citation_ids": sorted(ids - set(corpus)),
        })
        mapping.append({"review_id": review_id, "task_id": row["task_id"],
                        "seed": row["seed"], "mode": row["mode"],
                        "category": task["category"], "system_error": row["system_error"]})
    packets.sort(key=lambda p: p["review_id"])
    target = Path(output)
    target.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(protocol, target / "SEMANTIC_JUDGING.md")
    for name, value in (("judge_packets.json", packets), ("private_mapping.json", mapping)):
        (target / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in target.iterdir()}
    (target / "manifest.json").write_text(json.dumps({
        "runs_sha256": manifest["runs_sha256"], "packets": len(packets),
        "files_sha256": hashes, "labels_generated": False,
        "task_source_path": task_path, "task_source_sha256": manifest["sources"]["files_sha256"][task_path],
        "corpus_sha256": manifest["sources"]["files_sha256"][corpus_path],
        "exporter_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "protocol_timing": "Developed after pilots and during collection; not preregistered. Frozen here before any semantic judge execution.",
        "instructions": "Give the reviewer only judge_packets.json and SEMANTIC_JUDGING.md. Keep private_mapping.json private. Expert review of gold remains pending."
    }, indent=2) + "\n")
    return target


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    print(export(args.run_dir, args.output))
