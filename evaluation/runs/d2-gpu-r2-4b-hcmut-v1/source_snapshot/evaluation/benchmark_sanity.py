"""Benchmark sanity check with a cheap gateway model (no agent loop).

For each task the answer model answers (a) with only the gold source records as context ("oracle") and
(b) with no context ("closed_book"). A separate judge model compares each answer with the reference answer.
Low oracle scores point at questionable items (ambiguous question, wrong gold, missing context); high
closed-book scores point at items answerable without the corpus. Judgments are LLM estimates, not human labels.
"""
import argparse
import json
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Dict

import requests
import yaml

from evaluation.judge_gateway import local_environment

PROMPTS_CONFIG = Path("config/benchmark/sanity_prompts.yaml")
# Domain-neutral default of the judge prompt, kept as a module constant for importers (evaluation/benchmarks/qa/closed_book_neutral.py).
JUDGE_SYSTEM = ("You grade an answer against a reference answer for a Vietnamese question. "
                "Return JSON only: {\"verdict\": \"correct\"|\"partially_correct\"|\"incorrect\"|\"appropriate_refusal\"|"
                "\"inappropriate_refusal\", \"reason\": \"<one sentence>\"}. If the expected behaviour is refuse, "
                "\"appropriate_refusal\" means the answer says the information is not available; answering with "
                "invented content is \"incorrect\". Judge meaning, not wording.")


def domain_display_name(benchmark_dir: Path) -> str:
    """display_name of the benchmark's domain profile (benchmark.yaml `profile` -> config/domains/<id>.yaml)."""
    spec = yaml.safe_load((Path(benchmark_dir) / "benchmark.yaml").read_text(encoding="utf-8"))
    ref = str(spec["profile"])
    path = Path(ref) if ("/" in ref or ref.endswith((".yaml", ".yml"))) else Path("config/domains") / f"{ref}.yaml"
    return str(yaml.safe_load(path.read_text(encoding="utf-8"))["display_name"])


def build_prompts(display_name: str) -> Dict[str, str]:
    """answer_system / closed_system / judge_system for one domain, from config/benchmark/sanity_prompts.yaml."""
    templates = yaml.safe_load(PROMPTS_CONFIG.read_text(encoding="utf-8"))
    return {name: text.format(display_name=display_name) for name, text in templates.items()}


def chat(base, key, model, messages, max_tokens, json_mode=False):
    payload = {"model": model, "messages": messages, "max_tokens": max_tokens, "temperature": 0}
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    for attempt in range(3):
        try:
            r = requests.post(base + "/chat/completions", headers={"Authorization": f"Bearer {key}"},
                              json=payload, timeout=180)
            r.raise_for_status()
            d = r.json()
            return {"content": d["choices"][0]["message"]["content"] or "", "model": d.get("model"),
                    "usage": d.get("usage"), "error": None}
        except (requests.RequestException, KeyError, ValueError) as exc:
            error = f"{type(exc).__name__}: {exc}"
            time.sleep(2 * (attempt + 1))
    return {"content": None, "model": model, "usage": None, "error": error}


def run_task(task, corpus, base, key, answer_model, judge_model, prompts):
    gold = [corpus[i] for i in task["ground_truth_article_ids"] if i in corpus]
    if task["expected_behavior"] == "refuse":
        # Out-of-scope items: give the records a retriever would plausibly return is out of scope here;
        # the oracle context is the whole set of section titles, so refusal is judged without leaking an answer.
        context = "\n".join(f"- {r['doc_id']}: {r['title']}" for r in corpus.values())
    else:
        context = "\n\n".join(f"[{r['doc_id']}] {r['content']}" for r in gold)
    out = {"task_id": task["task_id"], "category": task["category"], "expected_behavior": task["expected_behavior"]}
    for mode, messages in {
        "oracle": [{"role": "system", "content": prompts["answer_system"]},
                   {"role": "user", "content": f"TÀI LIỆU:\n{context}\n\nCÂU HỎI: {task['question']}"}],
        "closed_book": [{"role": "system", "content": prompts["closed_system"]},
                        {"role": "user", "content": task["question"]}],
    }.items():
        answer = chat(base, key, answer_model, messages, 600)
        judged = None
        if answer["error"] is None:
            prompt = {"question": task["question"], "expected_behavior": task["expected_behavior"],
                      "reference_answer": task["expected_answer"], "candidate_answer": answer["content"]}
            # The judge may reason before answering; give it room and retry an unparseable reply (all attempts kept).
            attempts = []
            for _ in range(3):
                judge = chat(base, key, judge_model, [{"role": "system", "content": prompts["judge_system"]},
                                                      {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)}],
                             4096, json_mode=True)
                attempts.append(judge)
                try:
                    judged = json.loads(judge["content"]) if judge["error"] is None else {"error": judge["error"]}
                    break
                except (TypeError, ValueError):
                    judged = {"error": "judge returned invalid JSON", "raw": judge["content"]}
            judged["judge_attempts"] = len(attempts)
        out[mode] = {"answer": answer, "judgment": judged}
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark", help="benchmark name or directory: tasks, corpus and the domain wording of the prompts come from it")
    parser.add_argument("--tasks")
    parser.add_argument("--corpus")
    parser.add_argument("--domain-display-name", help="domain wording for the prompts when --benchmark is not given")
    parser.add_argument("--output", required=True)
    parser.add_argument("--answer-model", default="google/gemma-4-31b-it")
    parser.add_argument("--judge-model", default="deepseek/deepseek-v4-flash")
    parser.add_argument("--concurrency", type=int, default=4)
    args = parser.parse_args()
    if args.benchmark:
        directory = Path(args.benchmark) if Path(args.benchmark).is_dir() else Path("evaluation/benchmarks") / args.benchmark
        spec = yaml.safe_load((directory / "benchmark.yaml").read_text(encoding="utf-8"))
        args.tasks, args.corpus = args.tasks or str(directory / spec["tasks"]), args.corpus or spec["corpus"]
        display_name = args.domain_display_name or domain_display_name(directory)
    else:
        if not (args.tasks and args.corpus and args.domain_display_name):
            parser.error("give --benchmark, or --tasks, --corpus and --domain-display-name")
        display_name = args.domain_display_name
    prompts = build_prompts(display_name)
    env = local_environment()
    base, key = env["LUATCHECK_JUDGE_BASE_URL"].rstrip("/"), env["LUATCHECK_JUDGE_API_KEY"]
    tasks = json.loads(Path(args.tasks).read_text())
    corpus = {r["doc_id"]: r for r in json.loads(Path(args.corpus).read_text())}
    with ThreadPoolExecutor(args.concurrency) as pool:
        rows = list(pool.map(lambda t: run_task(t, corpus, base, key, args.answer_model, args.judge_model, prompts), tasks))
    summary = {}
    for mode in ("oracle", "closed_book"):
        verdicts = [((r[mode]["judgment"] or {}).get("verdict") or "error") for r in rows]
        summary[mode] = {v: verdicts.count(v) for v in sorted(set(verdicts))}
    result = {"answer_model": args.answer_model, "judge_model": args.judge_model, "tasks": args.tasks,
              "domain_display_name": display_name, "prompts": prompts,
              "note": "LLM answers and LLM judgments; not human labels.", "summary": summary, "rows": rows}
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=1))
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
