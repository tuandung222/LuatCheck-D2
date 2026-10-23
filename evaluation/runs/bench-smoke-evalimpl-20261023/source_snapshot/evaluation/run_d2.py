"""One command for the whole D2 matrix: benchmark x variant x seed -> preflight -> collect -> judge -> analyze -> tables -> notes.

  python evaluation/run_d2.py all --profile gpu-accuracy --run-dir evaluation/runs/d2-gpu-<stamp> --execute
  python evaluation/run_d2.py all --profile mac-latency  --run-dir evaluation/runs/d2-mac-<stamp> --execute
  python evaluation/run_d2.py preflight --profile gpu-accuracy          # every dependency exercised once, nothing written
  python evaluation/run_d2.py collect|judge|tables|notes|status --run-dir <dir>   # each stage alone
  python evaluation/run_d2.py compare <run-a> <run-b>                   # may these two runs be compared? (fingerprints)

What is run comes from config only: config/benchmark/d2_matrix.yaml (benchmarks, variants, seeds), variants.yaml, profile_*.yaml
(parallelism, timeouts, reranker runtime), model_prism_gguf2b.yaml (controller), judge_gateway.json (judge). Flags override the
matrix for smoke runs (--limit, --benchmarks, --variants, --seeds).

Resume: running the same command again continues the same run directory (append only; an incomplete last line is repaired,
backend outages are retried, drift of code/config/server is refused). Stages are idempotent: finished collection is skipped,
judged packets are never re-judged. Layout of evaluation/runs/<run-id>/: manifest.json, trials.jsonl, warmup.jsonl,
progress.json, preflight in the manifest, judge/, analysis/, tables/, RUN_NOTES.md, pipeline.log, source_snapshot/, state/.

Without --execute nothing is run or spent: the planned work and the judge-cost estimate are printed. AGENTS.md applies: real
inference only, failures are execution errors, nothing is filled in.
"""
import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import yaml

from evaluation import run_benchmark as rb

MATRIX_CONFIG = Path("config/benchmark/d2_matrix.yaml")
EXIT_JUDGE_UNAVAILABLE = 6
EXIT_COST_GUARD = 7


def load_matrix() -> Dict[str, Any]:
    return yaml.safe_load(MATRIX_CONFIG.read_text(encoding="utf-8")) or {}


def log(run_dir: Optional[Path], message: str) -> None:
    line = f"{datetime.now(timezone.utc).isoformat()} {message}"
    print(line, flush=True)
    if run_dir is not None and run_dir.exists():
        with (run_dir / "pipeline.log").open("a", encoding="utf-8") as stream:
            stream.write(line + "\n")


def selection(args, matrix: Dict[str, Any]) -> Dict[str, Any]:
    return {"benchmarks": args.benchmarks or matrix["benchmarks"],
            "variants": args.variants or ",".join(matrix["variants"]),
            "seeds": args.seeds or matrix["seeds"],
            "model_config": args.model_config or matrix["model_config"]}


def runner_args(args, matrix: Dict[str, Any], *, command: str) -> List[str]:
    sel = selection(args, matrix)
    out = [command]
    for bm in sel["benchmarks"]:
        out += ["--benchmark", bm]
    out += ["--variants", sel["variants"], "--seeds", *map(str, sel["seeds"]), "--run-profile", args.profile,
            "--model-config", sel["model_config"]]
    if args.endpoint:
        out += ["--endpoint", args.endpoint]
    if args.workers:
        out += ["--workers", str(args.workers)]
    if args.limit:
        out += ["--limit", str(args.limit)]
    if args.allow_unfrozen:
        out += ["--allow-unfrozen"]
    for flag in ("require_clean", "allow_build_drift", "skip_model_hash", "skip_canary", "allow_slot_mismatch"):
        if getattr(args, flag, False):
            out += ["--" + flag.replace("_", "-")]
    if args.run_dir:
        out += ["--output", args.run_dir]
    return out


def estimate_judge(args, matrix: Dict[str, Any]) -> Dict[str, Any]:
    sel = selection(args, matrix)
    plan_args = rb.build_parser().parse_args(runner_args(args, matrix, command="preflight"))
    benchmarks = rb.resolve_benchmarks(plan_args.benchmark)
    trials = 0
    for bm in benchmarks:
        trials += len(rb.select_tasks(bm.load_tasks(), args.limit)) * len(sel["seeds"]) * len(sel["variants"].split(","))
    cost = trials * matrix["planning_usd_per_packet"]
    judge_cfg = json.loads(Path(matrix["judge_config"]).read_text(encoding="utf-8"))
    attempts = trials * 1.45   # measured attempts per valid packet in the smoke run (26/18)
    hours = attempts * 49.0 / judge_cfg["concurrency"] / 3600   # 49 s median attempt wall time, measured in the same run
    return {"trials": trials, "judge_usd_estimate": round(cost, 2), "judge_hours_estimate": round(hours, 2),
            "basis": "planning figures measured in evaluation/runs/bench-smoke-both-20261023 (usd/packet, attempts/packet, s/attempt); not a quote"}


def collection_complete(run_dir: Path) -> bool:
    manifest_path = run_dir / "manifest.json"
    if not manifest_path.is_file():
        return False
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("status") != "collected":
        return False
    rows = rb.latest_by_key(rb.read_rows(rb.trials_path(run_dir)))
    return not any(rb.is_outage(r) for r in rows.values())


def stage_collect(args, matrix: Dict[str, Any], run_dir: Path) -> int:
    resuming = run_dir.exists()
    if resuming and collection_complete(run_dir):
        log(run_dir, "collect: already complete, skipped")
        return 0
    argv = runner_args(args, matrix, command="run") + ["--execute"]
    if resuming:
        argv += ["--resume", "--retry-errors"]
    if args.server_note:
        argv += ["--server-note", args.server_note]
    if args.trial_timeout:
        argv += ["--trial-timeout", str(args.trial_timeout)]
    log(run_dir if resuming else None, f"collect: {'resume' if resuming else 'start'} run_benchmark.py {' '.join(argv)}")
    code = rb.main(argv)
    log(run_dir, f"collect: finished with exit code {code}")
    return code


def judge_credential_available(matrix: Dict[str, Any]) -> bool:
    from evaluation.judge_gateway import local_environment
    cfg = json.loads(Path(matrix["judge_config"]).read_text(encoding="utf-8"))
    return bool(local_environment().get(cfg["credential_env"]))


def stage_judge(args, matrix: Dict[str, Any], run_dir: Path) -> int:
    from evaluation import judge_benchmark as jb
    if not judge_credential_available(matrix):
        log(run_dir, "judge: no gateway credential on this machine; stage NOT run. Copy the run directory to a machine that has it and run "
                     f"`python evaluation/run_d2.py judge --run-dir {run_dir} --execute`.")
        return EXIT_JUDGE_UNAVAILABLE
    info = jb.build_packets(run_dir)
    packets = json.loads((run_dir / "judge" / "judge_packets.json").read_text(encoding="utf-8"))
    state = jb.JudgeState(run_dir / "judge")
    todo = [p for p in packets if not any(a["status"] == "valid" for a in state.for_review(p["review_id"]))]
    estimate = len(todo) * matrix["planning_usd_per_packet"]
    log(run_dir, f"judge: {len(packets)} packets ({info['execution_errors_not_judged']} execution errors not judged), {len(todo)} to judge, "
                 f"estimated spend ~${estimate:.2f} (limit ${args.max_judge_usd or matrix['max_judge_usd']:.2f})")
    if estimate > (args.max_judge_usd or matrix["max_judge_usd"]):
        log(run_dir, "judge: estimate exceeds the spend limit; refusing. Raise --max-judge-usd after checking the figures.")
        return EXIT_COST_GUARD
    config = Path(matrix["judge_config"])
    summary = jb.run_judge(run_dir, config, execute=True, concurrency=args.judge_concurrency)
    log(run_dir, f"judge: round 1 {summary}")
    for round_number in range(2, 2 + int(matrix.get("judge_extra_rounds", 0))):
        if summary["invalid"] == 0:
            break
        summary = jb.run_judge(run_dir, config, execute=True, retry_invalid=True, concurrency=args.judge_concurrency)
        log(run_dir, f"judge: extra round {round_number - 1} {summary}")
    if summary["invalid"]:
        log(run_dir, f"judge: {summary['invalid']} packets stayed invalid after all attempts; they are reported as unknown (counted as failures), never dropped")
    return 0


def stage_analyze(run_dir: Path) -> Dict[str, Any]:
    from evaluation import judge_benchmark as jb
    jb.build_packets(run_dir)
    summary = jb.analyze(run_dir, audit_size=30)
    log(run_dir, f"analyze: report_eligible={summary['report_eligible']} coverage={summary['coverage']}")
    return summary


def stage_tables(run_dir: Path, matrix: Dict[str, Any], expect_benchmarks: List[str], expect_variants: List[str], allow_non_eligible: bool) -> int:
    from evaluation import render_benchmark_tables as render
    argv = ["--run-dir", str(run_dir), "--expect-benchmarks", ",".join(expect_benchmarks), "--expect-variants", ",".join(expect_variants)]
    summary = json.loads((run_dir / "analysis" / "summary.json").read_text(encoding="utf-8"))
    if allow_non_eligible or not summary["report_eligible"]:
        argv.append("--allow-non-eligible")
    code = render.main(argv)
    log(run_dir, f"tables: wrote {run_dir / 'tables'} (report_eligible={summary['report_eligible']}); publishing to report_d2 is a separate explicit step "
                 "(render_benchmark_tables.py --publish)")
    return code


# ----------------------------------------------------------------------------- notes

def recompute_headlines(run_dir: Path) -> Dict[str, Any]:
    """Independent re-computation of headline counts straight from trials.jsonl and judge/judgments.jsonl, with none of the analysis
    code, compared with analysis/summary.json. Recorded in RUN_NOTES so the tables are checked, not trusted."""
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    summary = json.loads((run_dir / "analysis" / "summary.json").read_text(encoding="utf-8"))
    rows = rb.latest_by_key(rb.read_rows(rb.trials_path(run_dir)))
    mapping = {(m["benchmark"], m["variant"], m["seed"], m["task_id"]): m["review_id"]
               for m in json.loads((run_dir / "judge" / "private_mapping.json").read_text(encoding="utf-8"))} if (run_dir / "judge" / "private_mapping.json").is_file() else {}
    judgments = {}
    jpath = run_dir / "judge" / "judgments.jsonl"
    if jpath.is_file():
        for line in jpath.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                if r["status"] == "valid":
                    judgments[r["review_id"]] = r["judgment"]
    checks = []
    for name, cell in summary["cells"].items():
        keys = [k for k in rows if k[0] == cell["benchmark"] and k[1] == cell["variant"]]
        statuses = [rows[k]["terminal_status"] for k in keys]
        successes = 0
        for k in keys:
            j = judgments.get(mapping.get(k))
            if rows[k]["system_error"] or not j or not j["judgeable"]:
                continue
            successes += bool(j["behaviour_appropriate"] and j["correctness"] == 2 and j["completeness"] == 2
                              and all(c["support"] == "supported" for c in j["claims"]))
        mine = {"trials": len(keys), "answered": statuses.count("answered"), "refused": statuses.count("refused"),
                "clarified": statuses.count("clarified"), "errors": statuses.count("error"), "strict_successes": successes}
        theirs = {"trials": cell["trials_recorded"], "answered": cell["counts"]["answered"], "refused": cell["counts"]["refused"],
                  "clarified": cell["counts"]["clarified"], "errors": cell["counts"]["execution_errors"],
                  "strict_successes": cell["strict_success"]["successes"]}
        checks.append({"cell": name, "independent": mine, "analysis": theirs, "match": mine == theirs})
    return {"all_match": all(c["match"] for c in checks), "cells": checks}


def write_notes(run_dir: Path) -> Path:
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    summary_path = run_dir / "analysis" / "summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.is_file() else None
    server, pre, git = manifest.get("server") or {}, manifest.get("preflight") or {}, manifest.get("git") or {}
    fingerprint = manifest.get("fingerprint") or {}
    rerank = (fingerprint.get("may_differ") or {}).get("reranker_runtime") or {}
    now = datetime.now().astimezone()
    lines = [f"# Run notes - `{manifest['run_id']}`", "",
             f"Generated {now.strftime('%Y-%m-%d %H:%M %Z')} by evaluation/run_d2.py from the run's own files (manifest, trials, judge, analysis). "
             "Facts below are copied from artifacts; nothing is estimated. The operator section at the end is for human remarks.", "",
             "## Run", "",
             f"- profile: `{manifest['run_profile']['name']}` (workers {manifest['run_profile'].get('workers_effective')}, latency reportable: {manifest['latency_reportable']}), phase `{manifest['phase']}`",
             f"- matrix: benchmarks {[b['name'] for b in manifest['benchmarks']]}, variants {list(manifest['variants'])}, seeds {manifest['seeds']}, limit {manifest.get('limit')}",
             f"- collection: status `{manifest['status']}`, planned {manifest.get('planned_trials')}, recorded {manifest.get('trials_recorded')}, "
             f"execution errors {manifest.get('execution_errors')} {manifest.get('error_kinds')}, resumes {len(manifest.get('resumes', []))}, "
             f"wall time in this/all sessions {manifest.get('wall_seconds_this_session')} / {manifest.get('wall_seconds_total')} s",
             f"- created {manifest['created_at']}, last finished {manifest.get('finished_at')}",
             f"- git: commit `{git.get('commit')}`, dirty {git.get('dirty')} ({git.get('tracked_changes')} tracked changes, {git.get('untracked_files')} untracked); "
             "the exact code is in `source_snapshot/`", "",
             "## Systems", "",
             f"- machine: {manifest['hardware'].get('platform')} / {manifest['hardware'].get('cpu_brand')} / python {manifest['hardware'].get('python')}; GPUs: {manifest['hardware'].get('nvidia_smi')}",
             f"- controller server: alias `{server.get('model_alias')}`, GGUF sha256 `{server.get('model_file_sha256')}`, ftype {server.get('model_ftype')}, build `{server.get('build_info')}`, "
             f"slots {server.get('total_slots')}, n_ctx {server.get('n_ctx')}, chat-template sha256 `{server.get('chat_template_sha256')}`",
             f"- server command line (local only): `{server.get('local_server_command')}`",
             f"- operator note on the server: {manifest.get('server_operator_note')}",
             f"- reranker runtime (variants that rerank): {json.dumps(rerank, ensure_ascii=False, default=str)}",
             f"- seed canary: {json.dumps({k: v for k, v in (pre.get('seed_canary') or {}).items() if k != 'texts'})}",
             f"- preflight warnings: {pre.get('warnings')}; failed checks: {pre.get('failed')}", ""]
    if summary:
        cost = summary["judge_cost_total"]
        lines += ["## Judge and analysis", "",
                  f"- judge: {json.dumps(summary.get('judge_model'), default=str)}",
                  f"- attempts {cost['attempts']} (valid {cost['valid_attempts']}, invalid share {cost.get('invalid_attempt_share')}), reasons {cost.get('invalid_reasons')}, "
                  f"gateway-reported cost ${cost['gateway_reported_usd_body']:.4f} (not an invoice), median attempt {((cost.get('attempt_wall_s') or {}).get('p50'))} s",
                  f"- coverage {summary['coverage']}; unknown trials {len(summary.get('unknown_trials', []))}; report_eligible **{summary['report_eligible']}** ({summary['report_eligible_note']})",
                  f"- human audit: `analysis/human-audit/` (labels blank until people label them); agreement/kappa: {'computed' if (run_dir / 'analysis/human-audit/agreement.json').is_file() else 'PENDING'}", ""]
        if (run_dir / "judge" / "judgments.jsonl").is_file():
            check = recompute_headlines(run_dir)
            lines += ["## Independent recomputation of the headline counts", "",
                      f"Counts of answered/refused/clarified/errors and strict successes per benchmark x variant recomputed from trials.jsonl and judge/judgments.jsonl "
                      f"without the analysis code: **{'ALL MATCH' if check['all_match'] else 'MISMATCH'}**", ""]
            for c in check["cells"]:
                lines.append(f"- {c['cell']}: {'match' if c['match'] else 'MISMATCH'} {c['independent']}")
            lines.append("")
    lines += ["## Operator notes", "",
              "PENDING: anomalies, manual steps, retries and who ran this must be written here by the operator; the tool does not guess them.", ""]
    path = run_dir / "RUN_NOTES.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    log(run_dir, f"notes: wrote {path}")
    return path


# ----------------------------------------------------------------------------- commands

def cmd_plan(args, matrix) -> int:
    sel = selection(args, matrix)
    est = estimate_judge(args, matrix)
    print(json.dumps({"profile": args.profile, "selection": sel, "limit": args.limit, "run_dir": args.run_dir, "judge_estimate": est,
                      "note": "dry run: pass --execute to collect and judge"}, indent=2))
    return 0


def cmd_all(args, matrix) -> int:
    if not args.run_dir:
        args.run_dir = f"evaluation/runs/d2-{args.profile}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    run_dir = Path(args.run_dir)
    if not args.execute:
        return cmd_plan(args, matrix)
    log(run_dir if run_dir.exists() else None, f"all: run dir {run_dir} ({'resume' if run_dir.exists() else 'new'}), profile {args.profile}")
    code = stage_collect(args, matrix, run_dir)
    if code != 0:
        log(run_dir, f"all: collection did not finish (exit {code}); fix the cause and run the SAME command again to resume")
        return code
    judge_code = 0
    if not args.skip_judge:
        judge_code = stage_judge(args, matrix, run_dir)
        if judge_code not in (0, EXIT_JUDGE_UNAVAILABLE):
            return judge_code
    else:
        log(run_dir, "all: judge skipped by --skip-judge")
    sel = selection(args, matrix)
    stage_analyze(run_dir)
    stage_tables(run_dir, matrix, [b for b in _bench_names(sel)], sel["variants"].split(","), allow_non_eligible=True)
    write_notes(run_dir)
    return judge_code if judge_code else 0


def _bench_names(sel: Dict[str, Any]) -> List[str]:
    if sel["benchmarks"] == ["all"]:
        return [p.parent.name for p in sorted(rb.BENCHMARKS_DIR.glob("*/benchmark.yaml"))]
    return [Path(b).name for b in sel["benchmarks"]]


def cmd_collect(args, matrix) -> int:
    if not args.execute:
        return cmd_plan(args, matrix)
    if not args.run_dir:
        raise rb.BenchmarkError("--run-dir is required")
    return stage_collect(args, matrix, Path(args.run_dir))


def cmd_judge(args, matrix) -> int:
    run_dir = Path(args.run_dir)
    if not args.execute:
        print("dry run: pass --execute to call the paid judge gateway")
        return 0
    code = stage_judge(args, matrix, run_dir)
    if code == 0:
        stage_analyze(run_dir)
    return code


def cmd_tables(args, matrix) -> int:
    run_dir = Path(args.run_dir)
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    if not (run_dir / "analysis" / "summary.json").is_file():
        stage_analyze(run_dir)
    code = stage_tables(run_dir, matrix, [b["name"] for b in manifest["benchmarks"]], list(manifest["variants"]), allow_non_eligible=True)
    write_notes(run_dir)
    return code


def cmd_notes(args, matrix) -> int:
    write_notes(Path(args.run_dir))
    return 0


def cmd_status(args, matrix) -> int:
    run_dir = Path(args.run_dir)
    code = rb.main(["status", "--run-dir", str(run_dir)])
    attempts = len(list((run_dir / "judge" / "attempts").glob("*.json"))) if (run_dir / "judge" / "attempts").is_dir() else 0
    packets = (json.loads((run_dir / "judge" / "judge_packets.json").read_text(encoding="utf-8")) if (run_dir / "judge" / "judge_packets.json").is_file() else [])
    print(f"judge: {len(packets)} packets built, {attempts} attempt files; summary: "
          f"{'analysis/summary.json present' if (run_dir / 'analysis' / 'summary.json').is_file() else 'not analysed'}")
    return code


def cmd_preflight(args, matrix) -> int:
    return rb.main(runner_args(args, matrix, command="preflight"))


def cmd_compare(args, matrix) -> int:
    a, b = (json.loads((Path(p) / "manifest.json").read_text(encoding="utf-8")) for p in (args.run_a, args.run_b))
    result = rb.compare_fingerprints(a.get("fingerprint") or {}, b.get("fingerprint") or {})
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0 if result["comparable"] else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("all", "preflight", "collect", "judge", "tables", "notes", "status"):
        p = sub.add_parser(name)
        p.add_argument("--profile", choices=sorted(rb.discover_profiles()), default="mac-latency")
        p.add_argument("--run-dir")
        p.add_argument("--benchmarks", nargs="+", help="override the matrix (smoke)")
        p.add_argument("--variants", help="comma list, override the matrix (smoke)")
        p.add_argument("--seeds", type=int, nargs="+")
        p.add_argument("--model-config")
        p.add_argument("--limit", type=int, help="smoke: N tasks per benchmark")
        p.add_argument("--allow-unfrozen", action="store_true", help="smoke only (needs --limit)")
        p.add_argument("--endpoint")
        p.add_argument("--workers")
        p.add_argument("--trial-timeout", type=float)
        p.add_argument("--server-note")
        p.add_argument("--require-clean", action="store_true")
        p.add_argument("--allow-build-drift", action="store_true")
        p.add_argument("--skip-model-hash", action="store_true")
        p.add_argument("--skip-canary", action="store_true")
        p.add_argument("--allow-slot-mismatch", action="store_true")
        p.add_argument("--skip-judge", action="store_true", help="collect + tables only; judge later where the gateway key exists")
        p.add_argument("--max-judge-usd", type=float, help="refuse the judge stage above this estimate")
        p.add_argument("--judge-concurrency", type=int)
        p.add_argument("--execute", action="store_true", help="explicit permission to run inference and to call the paid judge")
    cmp = sub.add_parser("compare")
    cmp.add_argument("run_a")
    cmp.add_argument("run_b")
    return parser


COMMANDS = {"all": cmd_all, "preflight": cmd_preflight, "collect": cmd_collect, "judge": cmd_judge, "tables": cmd_tables,
            "notes": cmd_notes, "status": cmd_status, "compare": cmd_compare}


def main(argv: Optional[List[str]] = None) -> int:
    os.chdir(REPO_ROOT)
    args = build_parser().parse_args(argv)
    matrix = load_matrix()
    try:
        return COMMANDS[args.command](args, matrix)
    except (rb.BenchmarkError, ValueError, FileNotFoundError) as exc:
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
