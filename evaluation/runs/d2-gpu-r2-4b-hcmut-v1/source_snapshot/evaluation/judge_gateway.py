"""Real API semantic judging of frozen blinded packets; no mock or fallback."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import time
import unicodedata
from urllib.parse import urlparse

import requests


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def local_environment():
    # Read only explicitly named local configuration; never search other projects.
    result = dict(os.environ)
    path = Path(".env")
    if path.exists():
        for line in path.read_text().splitlines():
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                result.setdefault(key.strip(), value.strip().strip("\"'"))
    return result


def normalized(text):
    return " ".join(unicodedata.normalize("NFC", text).split())


def validate(judgment, packet):
    """Validate schema/quoted spans only; never assign semantic support by regex."""
    required = {"review_id", "judgeable", "reference_issue", "behaviour_appropriate",
                "correctness", "completeness", "rationale", "claims"}
    if not isinstance(judgment, dict) or set(judgment) != required:
        raise ValueError("Judgment fields do not match required schema")
    if judgment["review_id"] != packet["review_id"] or type(judgment["judgeable"]) is not bool:
        raise ValueError("Invalid review identity/judgeable")
    if not isinstance(judgment["rationale"], str) or not judgment["rationale"].strip():
        raise ValueError("Rationale is required")
    if judgment["judgeable"]:
        if judgment["reference_issue"] is not None or type(judgment["behaviour_appropriate"]) is not bool:
            raise ValueError("Judgeable results require a resolved reference and behaviour label")
        if any(type(judgment[k]) is not int or judgment[k] not in (0, 1, 2)
               for k in ("correctness", "completeness")):
            raise ValueError("Invalid semantic scores")
    elif (not isinstance(judgment["reference_issue"], str) or not judgment["reference_issue"].strip()
          or any(judgment[k] is not None for k in ("behaviour_appropriate", "correctness", "completeness"))):
        raise ValueError("Unjudgeable results require issue and null scores")
    sources = {a["article_id"]: normalized(a["content"]) for a in packet["source_articles"]}
    answer = normalized(packet["candidate_answer"])
    if not isinstance(judgment["claims"], list):
        raise ValueError("claims must be a list")
    seen = set()
    for claim in judgment["claims"]:
        fields = {"answer_quote", "support", "source_article_id", "source_quote", "explanation"}
        if not isinstance(claim, dict) or set(claim) != fields:
            raise ValueError("Claim fields do not match schema")
        span = claim["answer_quote"]
        if not isinstance(span, str) or not span.strip() or normalized(span) not in answer:
            raise ValueError("Claim quote is absent from actual candidate answer")
        if normalized(span) in seen:
            raise ValueError("Duplicate claim quote")
        seen.add(normalized(span))
        if claim["support"] not in ("supported", "contradicted", "not_established"):
            raise ValueError("Unknown claim-support label")
        if not isinstance(claim["explanation"], str) or not claim["explanation"].strip():
            raise ValueError("Claim explanation is required")
        article, quote = claim["source_article_id"], claim["source_quote"]
        if claim["support"] in ("supported", "contradicted"):
            if article not in sources or not isinstance(quote, str) or not quote.strip() or normalized(quote) not in sources[article]:
                raise ValueError("Supporting/contradicting quote is absent from supplied source")
        else:
            # The frozen rubric does not require a supporting quotation for
            # not-established claims. A known relevant article may be named.
            if article is not None and article not in sources:
                raise ValueError("Optional source article is absent")
            if quote is not None and (article not in sources or not isinstance(quote, str)
                                      or not quote.strip() or normalized(quote) not in sources[article]):
                raise ValueError("Optional source quotation is invalid")
    if packet["candidate_behavior"] == "error" and judgment["judgeable"]:
        if judgment["behaviour_appropriate"] or judgment["correctness"] or judgment["completeness"]:
            raise ValueError("Execution error cannot be graded as appropriate/correct/complete")
    return judgment


def collect(packets_dir, config_path, output, *, execute=False, limit=None):
    if not execute:
        raise ValueError("No API calls without --execute")
    source = Path(packets_dir)
    cfg = json.loads(Path(config_path).read_text())
    env = local_environment()
    key = env.get(cfg["credential_env"], "")
    if not key:
        raise ValueError("Missing configured gateway credential; no substitute judge")
    if env.get("LUATCHECK_JUDGE_BASE_URL") != cfg["base_url"]:
        raise ValueError("Credential endpoint scope does not match judge configuration")
    if urlparse(cfg["base_url"]).scheme != "https":
        raise ValueError("Judge endpoint must use HTTPS")
    original = json.loads((source / "manifest.json").read_text())
    for name, expected in original["files_sha256"].items():
        if sha(source / name) != expected:
            raise ValueError("Blind packet/protocol hash mismatch")
    packets = json.loads((source / "judge_packets.json").read_text())
    if len(packets) != len({p["review_id"] for p in packets}) or len(packets) != original["packets"]:
        raise ValueError("Invalid blind-packet coverage")
    if limit is not None:
        packets = packets[:limit]
    target = Path(output)
    target.mkdir(parents=True, exist_ok=False)
    (target / "attempts").mkdir()
    shutil.copyfile(config_path, target / "config.json")
    for name in ("judge_packets.json", "SEMANTIC_JUDGING.md", "manifest.json"):
        shutil.copyfile(source / name, target / ("input-" + name))
    shutil.copyfile("evaluation/judge_prompt.txt", target / "judge_prompt.txt")
    shutil.copyfile(__file__, target / "judge_gateway.py")
    protocol = (target / "input-SEMANTIC_JUDGING.md").read_text()
    prompt = (target / "judge_prompt.txt").read_text()
    manifest = {"status": "collecting", "created_at": datetime.now(timezone.utc).isoformat(),
                "phase": "pilot" if limit else "main", "config": cfg,
                "source_runs_sha256": original["runs_sha256"],
                "expected_review_ids": [p["review_id"] for p in packets],
                "input_sha256": {p.name: sha(p) for p in target.iterdir() if p.is_file()},
                "human_labels": False, "human_judge_agreement": None,
                "actual_invoiced_charge_usd": None}

    def save():
        (target / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")

    save()

    def judge(packet):
        payload = {"model": cfg["model"], "messages": [
            {"role": "system", "content": prompt + "\n\nFROZEN PROTOCOL:\n" + protocol},
            {"role": "user", "content": "Evaluate this data packet as JSON:\n" + json.dumps(packet, ensure_ascii=False)}],
            "stream": False, "response_format": {"type": "json_object"},
            "thinking": cfg["thinking"], "reasoning_effort": cfg["reasoning_effort"],
            "max_tokens": cfg["max_tokens"]}
        row = {"review_id": packet["review_id"], "status": "invalid", "judgment": None, "attempts": []}
        for number in range(1, cfg["max_attempts"] + 1):
            record = {"review_id": packet["review_id"], "attempt": number, "request": payload,
                      "started_at": datetime.now(timezone.utc).isoformat(), "status": "error"}
            started = time.monotonic()
            fatal = False
            try:
                response = requests.post(cfg["base_url"].rstrip("/") + "/chat/completions",
                    headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
                    json=payload, timeout=cfg["timeout_seconds"], allow_redirects=False)
                record.update(http_status=response.status_code,
                              raw_body=response.text.replace(key, "[REDACTED_CREDENTIAL]"),
                              response_headers={k: v for k, v in response.headers.items()
                                                if k.lower() in {"x-request-id", "x-litellm-response-cost", "x-litellm-model-id", "x-litellm-version"}})
                if response.status_code != 200:
                    fatal = response.status_code in (401, 403, 404)
                    raise ValueError("Gateway returned HTTP " + str(response.status_code))
                data = response.json()
                record.update(returned_model=data.get("model"), usage=data.get("usage"))
                if data.get("model") not in cfg["allowed_returned_models"]:
                    fatal = True
                    raise ValueError("Gateway returned an unexpected model ID; no substitute judge accepted")
                choice = data["choices"][0]
                record["finish_reason"] = choice.get("finish_reason")
                if choice.get("finish_reason") != "stop":
                    raise ValueError("Judge completion is truncated or unfinished")
                judgment = validate(json.loads(choice["message"]["content"]), packet)
                record["status"] = "valid"
                row.update(status="valid", judgment=judgment)
            except Exception as exc:
                record["error"] = (type(exc).__name__ + ": " + str(exc)).replace(key, "[REDACTED_CREDENTIAL]")
            finally:
                record["wall_seconds"] = time.monotonic() - started
                name = f"{packet['review_id']}-a{number}.json"
                (target / "attempts" / name).write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
                row["attempts"].append(name)
            if row["status"] == "valid" or fatal:
                break
            if number < cfg["max_attempts"]:
                time.sleep(2 * number)
        return row

    rows = []
    try:
        with (target / "judgments.jsonl").open("x") as stream:
            with ThreadPoolExecutor(max_workers=cfg["concurrency"]) as pool:
                futures = [pool.submit(judge, p) for p in packets]
                for future in as_completed(futures):
                    row = future.result()
                    rows.append(row)
                    stream.write(json.dumps(row, ensure_ascii=False) + "\n")
                    stream.flush()
                    print(f"{len(rows)}/{len(packets)} {row['review_id']} {row['status']}", flush=True)
        manifest.update(status="collected_pending_human_validation", collected=len(rows),
                        valid=sum(r["status"] == "valid" for r in rows),
                        invalid=sum(r["status"] != "valid" for r in rows))
    except BaseException as exc:
        manifest.update(status="incomplete", collected=len(rows), error=type(exc).__name__)
        raise
    finally:
        if (target / "judgments.jsonl").exists():
            manifest["judgments_sha256"] = sha(target / "judgments.jsonl")
        manifest["attempts_sha256"] = {p.name: sha(p) for p in sorted((target / "attempts").glob("*.json"))}
        save()
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packets", required=True)
    parser.add_argument("--config", default="config/d2_judge_gateway.json")
    parser.add_argument("--output", required=True)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    result = collect(args.packets, args.config, args.output, execute=args.execute, limit=args.limit)
    print(json.dumps({k: result[k] for k in ("status", "collected", "valid", "invalid")}, indent=2))
