"""One real streamed retry for every invalid main judgment, never by its score."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import time

import requests

from evaluation.judge_gateway import local_environment, sha, validate


def recover(main_dir, output, execute=False):
    if not execute:
        raise ValueError("No API calls without --execute")
    root, target = Path(main_dir), Path(output)
    original = json.loads((root / "manifest.json").read_text())
    if original["status"] != "collected_pending_human_validation" or original["phase"] != "main":
        raise ValueError("Complete initial main judging first")
    if sha(root / "judgments.jsonl") != original["judgments_sha256"]:
        raise ValueError("Initial judgment hash mismatch")
    for name, digest in original["input_sha256"].items():
        if sha(root / name) != digest:
            raise ValueError("Frozen main input mismatch")
    rows = [json.loads(s) for s in (root / "judgments.jsonl").read_text().splitlines()]
    ids = {r["review_id"] for r in rows if r["status"] != "valid"}
    packets = [p for p in json.loads((root / "input-judge_packets.json").read_text()) if p["review_id"] in ids]
    if not ids or len(packets) != len(ids):
        raise ValueError("No invalid main judgments to recover, or coverage mismatch")
    cfg = dict(original["config"], max_tokens=16384, max_attempts=1, concurrency=2, stream=True)
    env = local_environment()
    if env.get("LUATCHECK_JUDGE_BASE_URL") != cfg["base_url"] or not env.get(cfg["credential_env"]):
        raise ValueError("Missing gateway-scoped credential")
    key = env[cfg["credential_env"]]
    target.mkdir(parents=True, exist_ok=False)
    (target / "attempts").mkdir()
    for name in ("input-judge_packets.json", "input-SEMANTIC_JUDGING.md", "judge_prompt.txt"):
        shutil.copyfile(root / name, target / name)
    shutil.copyfile(__file__, target / "recover_judge.py")
    shutil.copyfile("evaluation/judge_gateway.py", target / "judge_gateway.py")
    (target / "config.json").write_text(json.dumps(cfg, indent=2) + "\n")
    manifest = {"phase": "schema_failure_recovery", "status": "collecting", "config": cfg,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "initial_judgments_sha256": original["judgments_sha256"],
                "source_runs_sha256": original["source_runs_sha256"],
                "expected_review_ids": sorted(ids),
                "selection_rule": "All and only initial status != valid. No valid judgment resampled; no selection by semantic scores.",
                "protocol_development_note": "One streamed retry with 16384 output tokens was added after observing initial truncation/HTTP errors. Semantic prompts and task inputs are unchanged. Not preregistered.",
                "input_sha256": {p.name: sha(p) for p in target.iterdir() if p.is_file()},
                "human_labels": False}
    def save():
        (target / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    save()
    system = (target / "judge_prompt.txt").read_text() + "\n\nFROZEN PROTOCOL:\n" + (target / "input-SEMANTIC_JUDGING.md").read_text()
    def judge(packet):
        payload = {"model": cfg["model"], "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": "Evaluate this data packet as JSON:\n" + json.dumps(packet, ensure_ascii=False)}],
            "stream": True, "stream_options": {"include_usage": True},
            "response_format": {"type": "json_object"}, "thinking": cfg["thinking"],
            "reasoning_effort": cfg["reasoning_effort"], "max_tokens": cfg["max_tokens"]}
        record = {"review_id": packet["review_id"], "request": payload, "attempt": 1,
                  "started_at": datetime.now(timezone.utc).isoformat(), "status": "error"}
        row = {"review_id": packet["review_id"], "status": "invalid", "judgment": None,
               "attempts": [packet["review_id"] + "-a1.json"]}
        started, chunks, lines, content, reasoning = time.monotonic(), [], [], [], []
        try:
            with requests.post(cfg["base_url"].rstrip("/") + "/chat/completions",
                headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
                json=payload, stream=True, timeout=cfg["timeout_seconds"], allow_redirects=False) as response:
                record.update(http_status=response.status_code,
                              response_headers={k: v for k, v in response.headers.items() if k.lower() in
                                                {"x-request-id", "x-litellm-response-cost", "x-litellm-model-id", "x-litellm-version"}})
                if response.status_code != 200:
                    record["raw_body"] = response.text.replace(key, "[REDACTED_CREDENTIAL]")
                    raise ValueError("Gateway returned HTTP " + str(response.status_code))
                response.encoding = "utf-8"
                for line in response.iter_lines(decode_unicode=True):
                    lines.append(line)
                    if not line.startswith("data:"):
                        continue
                    body = line[5:].strip()
                    if body == "[DONE]":
                        record["done_marker_received"] = True
                        break
                    chunk = json.loads(body)
                    chunks.append(chunk)
                    if chunk.get("model"):
                        record["returned_model"] = chunk["model"]
                        if chunk["model"] not in cfg["allowed_returned_models"]:
                            raise ValueError("Unexpected returned model; no substitute accepted")
                    if chunk.get("usage") is not None:
                        record["usage"] = chunk["usage"]
                    for choice in chunk.get("choices", []):
                        delta = choice.get("delta") or {}
                        if delta.get("content"):
                            content.append(delta["content"])
                        if delta.get("reasoning_content"):
                            reasoning.append(delta["reasoning_content"])
                        if choice.get("finish_reason"):
                            record["finish_reason"] = choice["finish_reason"]
                record.update(assembled_content="".join(content), assembled_reasoning_content="".join(reasoning))
                if record.get("finish_reason") != "stop" or not record.get("done_marker_received"):
                    raise ValueError("Stream truncated or unfinished")
                judgment = validate(json.loads(record["assembled_content"]), packet)
                record["status"] = "valid"
                row.update(status="valid", judgment=judgment)
        except Exception as exc:
            record["error"] = (type(exc).__name__ + ": " + str(exc)).replace(key, "[REDACTED_CREDENTIAL]")
        finally:
            record["wall_seconds"] = time.monotonic() - started
            if lines:
                record["raw_body"] = "\n".join(lines).replace(key, "[REDACTED_CREDENTIAL]")
            record["stream_chunks"] = chunks
            (target / "attempts" / row["attempts"][0]).write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
        return row
    results = []
    try:
        with (target / "judgments.jsonl").open("x") as stream:
            with ThreadPoolExecutor(max_workers=cfg["concurrency"]) as pool:
                for future in as_completed([pool.submit(judge, p) for p in packets]):
                    row = future.result()
                    results.append(row)
                    stream.write(json.dumps(row, ensure_ascii=False) + "\n")
                    stream.flush()
                    print(f"{len(results)}/{len(packets)} {row['review_id']} {row['status']}", flush=True)
        manifest.update(status="collected_pending_human_validation", collected=len(results),
                        valid=sum(r["status"] == "valid" for r in results), invalid=sum(r["status"] != "valid" for r in results))
    except BaseException as exc:
        manifest.update(status="incomplete", error=type(exc).__name__)
        raise
    finally:
        if (target / "judgments.jsonl").exists():
            manifest["judgments_sha256"] = sha(target / "judgments.jsonl")
        manifest["attempts_sha256"] = {p.name: sha(p) for p in sorted((target / "attempts").glob("*.json"))}
        save()
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--main-dir", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    print(json.dumps(recover(args.main_dir, args.output, args.execute), ensure_ascii=False, indent=2))
