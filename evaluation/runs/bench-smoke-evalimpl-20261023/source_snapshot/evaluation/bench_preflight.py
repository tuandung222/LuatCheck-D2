"""Preflight for a benchmark collection: every dependency of the run is exercised once, for real, before the first trial.

Nothing is mocked and nothing is started: servers must already be running (this tool never starts or stops one). A failed
check with severity "error" refuses the run; "warn" is recorded in the manifest. The report is stored in the run manifest
(`preflight`) so the identity of what actually served the run (GGUF sha256, llama.cpp build, reranker runtime, sampler
defaults, seed behaviour, git state, machine load) is evidence, not an assumption.

Checks
  git          commit + dirty flag (error with require_clean)
  locks        every benchmark's lock hashes match the files (error unless a --limit smoke run)
  controller   server reachable, alias served, /health ok, GGUF sha256 / quantisation / llama.cpp build equal config/benchmark/expected_server.yaml,
               slots and context cover the workers, seed canary (same seed -> same text? different seed -> different text?)
  reranker     (only when a selected variant reranks) HTTP server health/props, or CUDA availability, then a REAL first-stage + rerank
               search through the same code path the agent uses, recording backend/model/device/dtype and the rerank wall time
  disk, load   free disk space; machine load average and the busiest processes (latency runs are perturbed by anything else running)
"""
import gc
import json
import os
import shutil
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import requests
import yaml

from evaluation import run_benchmark as rb

CANARY_PROMPT = "Viết một câu ngắn về mùa thu ở Hà Nội."


def _add(checks: List[Dict[str, Any]], name: str, ok: bool, detail: str, severity: str = "error", data: Optional[Dict[str, Any]] = None):
    checks.append({"name": name, "ok": bool(ok), "severity": severity if not ok else "info", "detail": detail, "data": data or {}})


def _base(endpoint: str) -> str:
    endpoint = endpoint.rstrip("/")
    return endpoint[:-3] if endpoint.endswith("/v1") else endpoint


def expected_server() -> Dict[str, Any]:
    path = rb.EXPECTED_SERVER_CONFIG
    return (yaml.safe_load(path.read_text(encoding="utf-8")) or {}) if path.is_file() else {}


def seed_canary(cfg) -> Dict[str, Any]:
    """Four real completions: seed A twice, seed B once, seed A once more, with the benchmark's sampler. Tells whether the
    server honours `seed` (different seeds should differ at temperature>0) and whether it is reproducible here."""
    url = cfg.model.endpoint.rstrip("/") + "/chat/completions"
    sampling = {"temperature": cfg.model.temperature, "top_p": cfg.model.top_p, "top_k": cfg.model.top_k,
                "min_p": cfg.model.min_p, "presence_penalty": cfg.model.presence_penalty}

    def ask(seed: int) -> str:
        payload = {"model": cfg.model.name, "messages": [{"role": "user", "content": CANARY_PROMPT}], "max_tokens": 48,
                   "stream": False, "seed": seed, "chat_template_kwargs": {"enable_thinking": False}, **sampling}
        response = requests.post(url, json=payload, timeout=60)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]

    first, again, other = ask(42), ask(42), ask(123)
    third = ask(42)
    return {"prompt": CANARY_PROMPT, "same_seed_identical": first == again == third, "different_seed_differs": first != other,
            "texts": {"seed42_a": first, "seed42_b": again, "seed123": other, "seed42_c": third}}


def machine_state() -> Dict[str, Any]:
    state: Dict[str, Any] = {"cpu_count": os.cpu_count()}
    try:
        state["load_average_1_5_15"] = [round(v, 2) for v in os.getloadavg()]
    except OSError:
        state["load_average_1_5_15"] = None
    top = rb._run(["ps", "-Ao", "pid,pcpu,rss,comm", "-r"] if sys.platform == "darwin" else ["ps", "-Ao", "pid,pcpu,rss,comm", "--sort=-pcpu"])
    if top:
        state["busiest_processes"] = top.splitlines()[:6]
    if shutil.which("nvidia-smi"):
        state["gpus"] = rb._run(["nvidia-smi", "--query-gpu=index,name,memory.used,memory.total,utilization.gpu", "--format=csv,noheader"])
        state["cuda_visible_devices"] = os.environ.get("CUDA_VISIBLE_DEVICES")
    return state


def reranker_check(checks, plan) -> None:
    rerank_variants = [v for v in plan["variant_names"] if rb.variant_needs_reranker(plan["variants"][v])]
    if not rerank_variants:
        return
    bm = plan["benchmarks"][0]
    cfg = rb.build_variant_config(plan["model_config"], bm, rerank_variants[0], plan["variants"][rerank_variants[0]],
                                  endpoint=plan["endpoint"], profile=plan["profile"])
    rr = cfg.retrieval.reranker
    runtime: Dict[str, Any] = {"backend": rr.backend, "model": rr.model, "device": rr.device, "dtype": rr.dtype,
                               "base_url": rr.base_url, "top_k_in": rr.top_k_in, "top_k_out": rr.top_k_out, "max_length": rr.max_length}
    if rr.backend in ("llamacpp_http", "qev_http"):
        base = rr.base_url.rstrip("/")
        try:
            health = requests.get(base + "/health", timeout=5)
            _add(checks, "reranker_server_health", health.status_code == 200, f"GET {base}/health -> HTTP {health.status_code}")
            try:
                props = requests.get(base + "/props", timeout=5)
                if props.status_code == 200:
                    p = props.json()
                    runtime["server_props"] = {k: p.get(k) for k in ("model_path", "build_info", "model_ftype", "model_alias", "total_slots")}
                    path = p.get("model_path")
                    if path and Path(path).is_file() and not plan.get("skip_model_hash"):
                        runtime["server_model_file_sha256"] = rb.sha256_file(path)
            except (requests.RequestException, ValueError):
                pass
        except requests.RequestException as exc:
            _add(checks, "reranker_server_health", False, f"reranker server not reachable at {base}: {type(exc).__name__}. "
                 "Start it first (see docs/RUNBOOK_D2.md); this tool never starts a server.", data=runtime)
            return
    elif rr.device in ("cuda", "auto") or str(rr.device).startswith("cuda"):
        try:
            import torch
            available = bool(torch.cuda.is_available())
            runtime["torch"] = torch.__version__
            runtime["cuda_available"] = available
            runtime["cuda_devices"] = [torch.cuda.get_device_name(i) for i in range(torch.cuda.device_count())] if available else []
            if str(rr.device).startswith("cuda") and not available:
                _add(checks, "reranker_cuda", False, f"profile asks for reranker device {rr.device!r} but torch.cuda is not available", data=runtime)
                return
        except ImportError as exc:
            _add(checks, "reranker_cuda", False, f"torch is required for the {rr.backend} reranker: {exc}", data=runtime)
            return
    # Real canary: the same code path as a search in a trial (first stage -> rerank), no controller call.
    from src.agent.loop import LuatCheckAgent
    task = bm.load_tasks()[0]
    try:
        agent = LuatCheckAgent(config=cfg, verification_mode=plan["variants"][rerank_variants[0]]["verification_mode"], l2_use_slm=False)
        started = time.monotonic()
        result, meta = agent.tool_registry.search_with_metadata(task["question"], 5)
        wall = time.monotonic() - started
        rerank = (meta or {}).get("rerank") or {}
        ok = bool(rerank.get("n_scored")) and bool(rerank.get("reranked_ids"))
        runtime.update({k: rerank.get(k) for k in ("backend", "model", "device", "dtype", "n_candidates", "n_scored", "n_truncated", "wall_ms")})
        runtime["canary_wall_s_including_load"] = round(wall, 2)
        _add(checks, "reranker_canary", ok, ("real rerank search scored %s candidates" % rerank.get("n_scored")) if ok else
             "search with reranker returned no rerank metadata", data=runtime)
    except Exception as exc:  # any failure here would be an execution error in every l1_rerank trial
        _add(checks, "reranker_canary", False, f"{type(exc).__name__}: {exc}", data=runtime)
    finally:
        try:
            del agent
        except NameError:
            pass
        gc.collect()
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except ImportError:
            pass


def run(plan: Dict[str, Any]) -> Dict[str, Any]:
    """plan keys: benchmarks, variant_names, variants, profile, workers, model_config, endpoint, smoke, first_cfg, output,
    require_clean, allow_build_drift, skip_model_hash, skip_canary."""
    checks: List[Dict[str, Any]] = []
    git = rb.git_state()
    relevant = rb._run(["git", "status", "--porcelain", "--", "src", "config", "evaluation/run_benchmark.py", "evaluation/metrics.py",
                        "evaluation/bench_preflight.py"]) or ""
    git["dirty_in_collection_paths"] = [line for line in relevant.splitlines() if line]
    git["describe"] = rb._run(["git", "describe", "--always", "--dirty", "--abbrev=12"])
    if git["commit"] is None:
        _add(checks, "git", True, "not a git checkout (e.g. a synced copy); the source snapshot and hashes identify the code", "warn", git)
    else:
        clean = not git["dirty_in_collection_paths"]
        _add(checks, "git", clean or not plan.get("require_clean"),
             f"commit {git['commit'][:12]}, {'clean' if clean else str(len(git['dirty_in_collection_paths'])) + ' uncommitted paths in collection code/config (recorded; the snapshot holds the exact bytes)'}",
             "error" if plan.get("require_clean") else "warn", git)

    for bm in plan["benchmarks"]:
        state, problems = rb.lock_status(bm)
        _add(checks, f"lock:{bm.name}", state == "ok" or plan["smoke"], f"lock {state}" + (": " + "; ".join(problems) if problems else ""),
             "error", {"problems": problems})

    first_cfg = plan["first_cfg"]
    expected = expected_server()
    try:
        server = rb.server_info(first_cfg, sha_model=not plan.get("skip_model_hash"))
    except rb.BenchmarkError as exc:
        _add(checks, "controller", False, str(exc))
        return _finish(checks, plan, git, None, None)
    _add(checks, "controller", True, f"{server['endpoint']} serves {server['model_alias']} (slots {server.get('total_slots')}, n_ctx {server.get('n_ctx')})",
         data={k: server.get(k) for k in ("model_path", "build_info", "model_ftype", "total_slots", "n_ctx")})
    try:
        health = requests.get(_base(server["endpoint"]) + "/health", timeout=5)
        _add(checks, "controller_health", health.status_code == 200, f"/health HTTP {health.status_code}")
    except requests.RequestException as exc:
        _add(checks, "controller_health", False, f"/health failed: {type(exc).__name__}")
    if expected:
        want_sha = expected.get("gguf_sha256")
        if want_sha:
            if server.get("model_file_sha256"):
                _add(checks, "controller_gguf_sha256", server["model_file_sha256"] == want_sha,
                     f"GGUF sha256 {server['model_file_sha256'][:16]}.. {'==' if server['model_file_sha256'] == want_sha else '!='} expected {want_sha[:16]}..")
            else:
                _add(checks, "controller_gguf_sha256", False, "GGUF file not readable from this machine: identity not verified", "warn")
        if expected.get("quantisation") and server.get("model_ftype"):
            _add(checks, "controller_quantisation", expected["quantisation"] in str(server["model_ftype"]),
                 f"server ftype {server['model_ftype']!r}, expected to contain {expected['quantisation']!r}")
        if expected.get("llama_cpp_commit") and server.get("build_info"):
            same = str(expected["llama_cpp_commit"]) in str(server["build_info"])
            _add(checks, "controller_llama_cpp_build", same or plan.get("allow_build_drift"),
                 f"server build {server['build_info']!r}, expected commit {expected['llama_cpp_commit']!r}" +
                 ("" if same else " (different build: results are not comparable with other machines)"), "error")
        if expected.get("alias"):
            _add(checks, "controller_alias", server["model_alias"] == expected["alias"], f"alias {server['model_alias']!r}")
    workers = plan["workers"]
    if workers > 1:
        slots, n_ctx = server.get("total_slots"), server.get("n_ctx")
        _add(checks, "controller_slots", bool(slots) and slots >= workers or plan.get("allow_slot_mismatch", False),
             f"{workers} workers vs {slots} slots (-np)")
        need = first_cfg.model.context_tokens * workers
        _add(checks, "controller_context", (not n_ctx) or n_ctx >= need, f"server -c {n_ctx}, needs >= {need} ({first_cfg.model.context_tokens} x {workers} workers)")
    canary = None
    if not plan.get("skip_canary"):
        try:
            canary = seed_canary(first_cfg)
            _add(checks, "seed_honoured", canary["different_seed_differs"],
                 "different seeds produced different text" if canary["different_seed_differs"] else "different seeds gave identical text: the server may ignore `seed`",
                 "warn", {k: v for k, v in canary.items() if k != "texts"})
            _add(checks, "seed_reproducible", canary["same_seed_identical"],
                 "same seed reproduced the same text" if canary["same_seed_identical"] else
                 "same seed gave different text here: seeds select a sampling stream but runs are not bit-reproducible", "warn")
        except (requests.RequestException, KeyError, ValueError) as exc:
            _add(checks, "seed_canary", False, f"canary completion failed: {type(exc).__name__}: {exc}")
    reranker_check(checks, plan)

    out_parent = Path(plan["output"]).resolve().parent
    out_parent.mkdir(parents=True, exist_ok=True)
    free_gb = shutil.disk_usage(out_parent).free / 1e9
    _add(checks, "disk", free_gb >= 2.0, f"{free_gb:.1f} GB free at {out_parent}")
    machine = machine_state()
    load = (machine.get("load_average_1_5_15") or [0])[0]
    busy = load > 0.5 * (machine["cpu_count"] or 1)
    _add(checks, "machine_idle", not busy, f"1-min load average {load} on {machine['cpu_count']} CPUs" +
         (" (busy: other work perturbs timings)" if busy else ""), "warn", machine)
    return _finish(checks, plan, git, server, canary)


def _finish(checks, plan, git, server, canary) -> Dict[str, Any]:
    failed = [c for c in checks if not c["ok"] and c["severity"] == "error"]
    return {"ok": not failed, "generated_at": rb.utcnow(), "failed": [c["name"] for c in failed],
            "warnings": [c["name"] for c in checks if not c["ok"] and c["severity"] == "warn"],
            "checks": checks, "git": git, "server": server, "seed_canary": canary,
            "run_profile": plan["profile"]["name"], "workers": plan["workers"]}
