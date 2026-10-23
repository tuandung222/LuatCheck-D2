"""Native-only D2 collection. No inference runs without --execute."""
import argparse
import hashlib
import json
import platform
import subprocess
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import sys
from urllib.parse import urlparse

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import requests

from src.agent.loop import LuatCheckAgent
from src.agent.llm_client import GatewayLLMClient, LlamaCppLLMClient, MlxVlmLLMClient, OllamaLLMClient
from src.config.app_config import load_config
from evaluation.metrics import calculate_citation_metrics, calculate_retrieval_metrics, calculate_unsupported_rate


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def preflight_gateway(cfg):
    """Diagnostic remote controller: confirm the model is listed; never store the credential."""
    client = GatewayLLMClient(cfg.model.endpoint, cfg.model.api_key_env)
    response = requests.get(cfg.model.endpoint.rstrip("/") + "/models",
                            headers={"Authorization": f"Bearer {client._api_key()}"}, timeout=30)
    response.raise_for_status()
    listed = {m.get("id") for m in response.json().get("data", [])}
    if cfg.model.name not in listed:
        raise RuntimeError("Configured gateway model is not listed. No substitute will be attempted.")
    return {"model": {"name": cfg.model.name, "digest": None, "revision_pinned": False},
            "endpoint_host": urlparse(cfg.model.endpoint).hostname, "provider": "gateway",
            "protocol_note": "Diagnostic remote controller; not the frozen local D2 protocol.",
            "inference_executed": False}


def preflight_mlx(cfg):
    """Diagnostic local MLX controller: model loaded on a loopback mlx_vlm.server, HF revision recorded."""
    endpoint = cfg.model.endpoint.rstrip("/")
    if urlparse(endpoint).hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError("MLX collection is restricted to a loopback endpoint.")
    response = requests.get(endpoint + "/models", timeout=5)
    response.raise_for_status()
    entry = next((m for m in response.json().get("data", []) if m.get("id") == cfg.model.name), None)
    if not entry or not entry.get("loaded"):
        raise RuntimeError("Configured MLX model is not loaded on the server. No substitute will be attempted.")
    ref = Path.home() / ".cache/huggingface/hub" / ("models--" + cfg.model.name.replace("/", "--")) / "refs/main"
    return {"model": {"name": cfg.model.name, "digest": None,
                      "hf_revision": ref.read_text().strip() if ref.exists() else None},
            "endpoint": endpoint, "provider": "mlx",
            "protocol_note": "Diagnostic local MLX controller; not the frozen D2 protocol.",
            "inference_executed": False}


def preflight_llamacpp(cfg):
    """Diagnostic local llama.cpp controller: alias served on loopback; GGUF path, hash and build recorded."""
    endpoint = cfg.model.endpoint.rstrip("/")
    if urlparse(endpoint).hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError("llama.cpp collection is restricted to a loopback endpoint.")
    listed = requests.get(endpoint + "/models", timeout=5)
    listed.raise_for_status()
    if cfg.model.name not in {m.get("id") for m in listed.json().get("data", [])}:
        raise RuntimeError("Configured llama.cpp model alias is not served. No substitute will be attempted.")
    base = endpoint[:-3] if endpoint.endswith("/v1") else endpoint
    props = requests.get(base + "/props", timeout=5).json()
    path = props.get("model_path")
    return {"model": {"name": cfg.model.name, "digest": sha256(path) if path and Path(path).exists() else None,
                      "model_path": path, "build_info": props.get("build_info"),
                      "n_ctx": props.get("default_generation_settings", {}).get("n_ctx")},
            "endpoint": endpoint, "provider": "llamacpp",
            "protocol_note": "Diagnostic local llama.cpp controller; not the frozen D2 protocol.",
            "inference_executed": False}


def preflight(config_path="config/d2_native.yaml"):
    cfg = load_config(config_path)
    if cfg.model.provider == "gateway":
        return preflight_gateway(cfg)
    if cfg.model.provider == "mlx":
        return preflight_mlx(cfg)
    if cfg.model.provider == "llamacpp":
        return preflight_llamacpp(cfg)
    if cfg.model.provider != "ollama":
        raise ValueError("D2 collection supports Ollama (frozen protocol) or a diagnostic gateway only.")
    endpoint = cfg.model.endpoint.rstrip("/")
    if urlparse(endpoint).hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError("D2 collection is restricted to a loopback native endpoint.")
    tags_response = requests.get(endpoint + "/api/tags", timeout=5)
    tags_response.raise_for_status()
    models = tags_response.json().get("models", [])
    model = next((m for m in models if m.get("name") == cfg.model.name or m.get("model") == cfg.model.name), None)
    if not model or not model.get("digest"):
        raise RuntimeError("Configured model with a digest is not present. No download or substitute will be attempted.")
    version_response = requests.get(endpoint + "/api/version", timeout=5)
    version_response.raise_for_status()
    return {"model": model, "ollama_version": version_response.json(),
            "endpoint": endpoint, "provider": "ollama", "inference_executed": False}


def validate_tasks(tasks_file, review_file=None, phase="pilot"):
    tasks = json.loads(Path(tasks_file).read_text())
    ids = [t["task_id"] for t in tasks]
    if not tasks or len(ids) != len(set(ids)):
        raise ValueError("Task set must be nonempty with unique IDs.")
    for task in tasks:
        if not task.get("question") or "expected_behavior" not in task:
            raise ValueError("Every frozen task requires a question and explicit expected_behavior.")
        if task["expected_behavior"] not in {"answer", "clarify", "refuse"}:
            raise ValueError("Invalid expected_behavior.")
    if phase == "main":
        if not review_file:
            raise ValueError("Main collection requires a reviewed task manifest.")
        review = json.loads(Path(review_file).read_text())
        if review.get("status") != "approved":
            raise ValueError("Task review manifest has not been approved.")
        if review.get("tasks_sha256") != sha256(tasks_file):
            raise ValueError("Task review does not match the frozen dataset.")
        review_rows = review.get("tasks", [])
        reviewed = {r["task_id"]: r for r in review_rows}
        if len(reviewed) != len(review_rows) or set(reviewed) != set(ids):
            raise ValueError("Task review must cover the frozen IDs exactly once.")
        for tid in ids:
            row = reviewed.get(tid, {})
            if row.get("status") != "approved" or not all(row.get(k) for k in ["reviewer", "source_note", "gold_check"]):
                raise ValueError(f"Task {tid} needs provenance and gold review before main collection.")
    return tasks


def source_manifest(tasks_file, config_path):
    paths = sorted(Path("src").rglob("*.py")) + sorted(Path("evaluation").glob("*.py"))
    paths += [Path(tasks_file), Path(config_path), Path("requirements.txt")]
    benchmark_dir = Path(tasks_file).parent
    paths += [p for p in sorted(benchmark_dir.glob("*.json")) if p not in paths]
    paths += sorted(Path("data/corpus").glob("*.json"))
    paths += [p for p in [Path("docs/materials/benchmark-sources/bll2019-congbao.pdf"),
                         Path("docs/materials/benchmark-sources/corpus_manifest.json"),
                         Path("docs/materials/benchmark-sources/extract_official_corpus.py")]
              if p.exists()]
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    return {"base_commit": commit, "tracked_worktree_dirty": bool(subprocess.check_output(["git", "diff", "--name-only"], text=True).strip()),
            "files_sha256": {str(p): sha256(p) for p in paths}}


def collect_runs(tasks_file, seeds, modes, config_path, output_dir, *, execute=False,
                 phase="pilot", task_review=None):
    if not execute:
        raise ValueError("Collection is disabled without explicit execute=True / --execute.")
    if len(seeds) != len(set(seeds)) or not seeds:
        raise ValueError("Seeds must be nonempty and unique.")
    if set(modes) - {"off", "l1_on"} or len(modes) != len(set(modes)) or not modes:
        raise ValueError("D2 uses OFF and/or L1 ON only. Extra judge ablations are a separate protocol.")
    tasks = validate_tasks(tasks_file, task_review, phase)
    cfg = load_config(config_path)
    if cfg.retrieval.dense_model_type not in {"tfidf", "bm25"}:
        raise ValueError("D2 freezes an explicit local statistical retriever; neural ablations need a separate protocol.")
    if phase == "main":
        review = json.loads(Path(task_review).read_text())
        if review.get("corpus_sha256") != sha256(cfg.retrieval.corpus_path):
            raise ValueError("Approved task review does not match the corpus snapshot.")
    metadata = preflight(config_path)
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=False)
    start = time.monotonic()
    manifest = {"schema": "luatcheck.native.d2.v1", "phase": phase,
                "created_at": datetime.now(timezone.utc).isoformat(), "status": "collecting",
                "report_eligible": False, "model": metadata, "config": cfg.model_dump(),
                "sources": source_manifest(tasks_file, config_path), "seeds": seeds, "modes": modes,
                "task_ids": [t["task_id"] for t in tasks], "platform": platform.platform(),
                "scoring": "Citation/retrieval/lexical proxies; human correctness labels remain pending.",
                "device_active_GPU_hours": None,
                "API_charge_USD": 0.0 if metadata["provider"] != "gateway" else None,
                "API_charge_note": ("Local endpoint; this is not a claim of zero compute cost."
                                    if metadata["provider"] != "gateway" else
                                    "Gateway-reported per-call usage.cost is retained in each native_response; not an invoice.")}
    def save_manifest():
        (target / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    save_manifest()
    rows = []
    try:
        # Preserve the exact sources even when preparing from an uncommitted checkout.
        for source, expected_hash in manifest["sources"]["files_sha256"].items():
            if sha256(source) != expected_hash:
                raise RuntimeError("Source changed while freezing the collection snapshot.")
            try:
                relative = Path(source).resolve().relative_to(Path.cwd())
            except ValueError:
                relative = Path("external") / (expected_hash[:12] + "-" + Path(source).name)
            destination = target / "source_snapshot" / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
            if sha256(destination) != expected_hash:
                raise RuntimeError("Copied source snapshot does not match its manifest.")
        if task_review:
            manifest["task_review_sha256"] = sha256(task_review)
            shutil.copyfile(task_review, target / "task_review.json")
        agents = {}
        for mode in modes:
            local_cfg = cfg.model_copy(deep=True)
            local_cfg.memory.sqlite_path = str(target / f"state-{mode}.db")
            local_cfg.memory.enabled = False
            local_cfg.security.audit_log_path = str(target / f"audit-{mode}.jsonl")
            local_cfg.security.outbox_path = str(target / f"outbox-{mode}.jsonl")
            a = LuatCheckAgent(config=local_cfg, verification_mode=mode, l2_use_slm=False)
            expected_client = {"gateway": GatewayLLMClient, "mlx": MlxVlmLLMClient, "llamacpp": LlamaCppLLMClient}.get(metadata["provider"], OllamaLLMClient)
            if type(a.llm_client) is not expected_client:
                raise TypeError("The configured real inference client is required for collection.")
            agents[mode] = a
        with (target / "runs.jsonl").open("w") as stream:
            for seed in seeds:
                for index, task in enumerate(tasks):
                    order = modes if index % 2 == 0 else list(reversed(modes))
                    for mode in order:
                        agent = agents[mode]
                        agent.llm_client.seed = seed
                        before = time.monotonic()
                        ledger = agent.run(task["question"], pasted_doc=task.get("pasted_doc"),
                                           session_id=f"{mode}-s{seed}-{task['task_id']}")
                        calls = ledger.llm_calls
                        genuine = bool(calls) and all(c.get("backend") == metadata["provider"] for c in calls)
                        success_calls = sum(c["outcome"] == "success" for c in calls)
                        backend_error = ledger.terminal_status == "error"
                        if ledger.terminal_status == "answered" and (not genuine or not success_calls):
                            raise RuntimeError("Answer without native inference is ineligible.")
                        final = ledger.final_output or {}
                        policy_refusal = not calls and ledger.terminal_status == "refused" and final.get("pre_model_policy_refusal") is True
                        tokens_complete = policy_refusal or bool(calls) and all(isinstance(c.get(k), int) and not isinstance(c.get(k), bool)
                                                             for c in calls for k in ["input_tokens", "output_tokens"])
                        final = ledger.final_output or {}
                        citations = final.get("citations", [])
                        ids = [c["article_id"] for c in citations]
                        gold = task.get("ground_truth_article_ids", [])
                        row = {"task_id": task["task_id"], "seed": seed, "mode": mode,
                               "expected_behavior": task["expected_behavior"], "terminal_status": ledger.terminal_status,
                               "gold_article_ids": gold,
                               "system_error": backend_error, "error_kind": final.get("error_kind"),
                               "pre_model_policy_refusal": policy_refusal,
                               "native_calls": len(calls), "successful_native_calls": success_calls,
                               "wall_ms": round((time.monotonic()-before)*1000, 3),
                               "token_usage_complete": tokens_complete,
                               "input_tokens": sum(c["input_tokens"] for c in calls) if tokens_complete else None,
                               "output_tokens": sum(c["output_tokens"] for c in calls) if tokens_complete else None,
                               "retrieval": calculate_retrieval_metrics(ledger.retrieved_article_ids, gold),
                               "citation": calculate_citation_metrics(ids, gold),
                               "lexical_unsupported_proxy": (calculate_unsupported_rate(final.get("content", ""), citations,
                                                                                       agent.verifier, ledger.retrieved_article_ids)
                                                              if ledger.terminal_status == "answered" else None),
                               "human_task_correct": None, "human_unsupported_claims": None,
                               "ledger": ledger.model_dump()}
                        stream.write(json.dumps(row, ensure_ascii=False) + "\n")
                        stream.flush()
                        rows.append(row)
                        print(f"{task['task_id']} seed={seed} {mode} {ledger.terminal_status}", flush=True)
                        if backend_error and final.get("error_kind") == "backend_error":
                            raise RuntimeError("Backend/output failure: collection stopped. Partial records retained; no success summary.")
        manifest.update(status="collected_pending_human_scoring", completed_runs=len(rows),
                        report_eligible=False, tokens_complete=all(r["token_usage_complete"] for r in rows))
    except BaseException as exc:
        manifest.update(status="incomplete", completed_runs=len(rows), failure=f"{type(exc).__name__}: {exc}")
        raise
    finally:
        manifest["device_run_wall_hours"] = (time.monotonic()-start)/3600
        manifest["wall_time_note"] = "Device collection wall time, not measured active GPU hours."
        if (target / "runs.jsonl").exists():
            manifest["runs_sha256"] = sha256(target / "runs.jsonl")
        save_manifest()
    return {"run_dir": str(target), "runs": len(rows), "status": manifest["status"], "report_eligible": False}


def run_benchmark(tasks_file: str, seeds: List[int], mode="l1_on", l2_use_slm=False, offline=False,
                  *, execute=False, config_path="config/d2_native.yaml", output_dir=None,
                  phase="pilot", task_review=None) -> Dict[str, Any]:
    if offline:
        raise ValueError("offline=True previously generated mock results and is forbidden. A local native server is required.")
    if l2_use_slm:
        raise ValueError("SLM judge evaluation is outside the frozen D2 protocol.")
    if output_dir is None:
        raise ValueError("Use a fresh explicit output directory; historical results are never overwritten.")
    return collect_runs(tasks_file, seeds, [mode], config_path, output_dir,
                        execute=execute, phase=phase, task_review=task_review)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config/d2_native.yaml")
    parser.add_argument("--tasks", default="evaluation/benchmarks/bll2019_v1/tasks.json")
    parser.add_argument("--seeds", type=int, nargs="+", default=[42, 123, 2026])
    parser.add_argument("--ablation", choices=["both", "on", "off"], default="both")
    parser.add_argument("--phase", choices=["pilot", "main"], default="pilot")
    parser.add_argument("--task-review")
    parser.add_argument("--output", help="A new directory; existing paths are refused.")
    parser.add_argument("--preflight-only", action="store_true", help="Read model/version metadata; no generation.")
    parser.add_argument("--execute", action="store_true", help="Explicit permission to start native inference.")
    args = parser.parse_args()
    if args.preflight_only:
        print(json.dumps(preflight(args.config), ensure_ascii=False, indent=2))
        return
    if not args.execute or not args.output:
        parser.error("No experiment started. Provide --execute and a new --output directory.")
    modes = ["off", "l1_on"] if args.ablation == "both" else (["off"] if args.ablation == "off" else ["l1_on"])
    print(json.dumps(collect_runs(args.tasks, args.seeds, modes, args.config, args.output,
                                 execute=True, phase=args.phase, task_review=args.task_review), ensure_ascii=False))


if __name__ == "__main__":
    main()
