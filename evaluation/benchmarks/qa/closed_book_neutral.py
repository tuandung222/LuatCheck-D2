#!/usr/bin/env python3
"""Closed-book guessability probe for labour_vi_v1 with a NEUTRAL prompt (BENCHMARK-QA, 2026-10-23).

Why: evaluation/benchmark_sanity.py hard-codes an HCMUT-scoped CLOSED_SYSTEM prompt, so the labour sanity runs'
closed-book column mostly shows scope refusals (48/50 answers mention the HCMUT scope). This re-asks the 45
answerable labour questions with a labour-law prompt. Answers and verdicts are LLM estimates, not human labels.
Reads tasks only; the key comes from evaluation.judge_gateway.local_environment and is never printed/stored.
"""
import argparse, json, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from evaluation.benchmark_sanity import chat, JUDGE_SYSTEM  # noqa: E402  (reuse the project's own helpers)
from evaluation.judge_gateway import local_environment  # noqa: E402

SYSTEM = ("Trả lời ngắn gọn bằng tiếng Việt câu hỏi về pháp luật lao động, công đoàn, việc làm và bảo hiểm của Việt Nam. "
          "Hãy đưa ra câu trả lời cụ thể nhất theo hiểu biết của bạn; chỉ nói không biết nếu thực sự không có thông tin.")

ap = argparse.ArgumentParser()
ap.add_argument("--benchmark", default="labour_vi_v1")
ap.add_argument("--out", required=True)
ap.add_argument("--answer-model", default="google/gemma-4-31b-it")
ap.add_argument("--judge-model", default="deepseek/deepseek-v4-flash")
a = ap.parse_args()
env = local_environment()
base, key = env["LUATCHECK_JUDGE_BASE_URL"].rstrip("/"), env["LUATCHECK_JUDGE_API_KEY"]
tasks = [t for t in json.loads((ROOT / f"evaluation/benchmarks/{a.benchmark}/tasks.json").read_text()) if t["expected_behavior"] == "answer"]


def one(t):
    ans = chat(base, key, a.answer_model, [{"role": "system", "content": SYSTEM}, {"role": "user", "content": t["question"]}], 600)
    j = None
    if ans["error"] is None:
        prompt = {"question": t["question"], "expected_behavior": "answer", "reference_answer": t["expected_answer"], "candidate_answer": ans["content"]}
        for _ in range(3):
            jr = chat(base, key, a.judge_model, [{"role": "system", "content": JUDGE_SYSTEM}, {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)}], 4096, json_mode=True)
            try:
                j = json.loads(jr["content"]); j["cost"] = (jr.get("usage") or {}).get("cost"); break
            except (TypeError, ValueError):
                j = {"error": "invalid judge JSON"}
    return {"task_id": t["task_id"], "answer": ans["content"], "answer_error": ans["error"], "answer_cost": (ans.get("usage") or {}).get("cost"), "judgment": j}


with ThreadPoolExecutor(4) as pool:
    rows = list(pool.map(one, tasks))
summ = {}
for r in rows:
    v = (r["judgment"] or {}).get("verdict", "error"); summ[v] = summ.get(v, 0) + 1
cost = sum(float(r.get("answer_cost") or 0) + float((r["judgment"] or {}).get("cost") or 0) for r in rows)
Path(a.out).write_text(json.dumps({"note": "LLM answers + LLM judgments with a neutral prompt; not human labels.", "answer_model": a.answer_model, "judge_model": a.judge_model,
                                   "system_prompt": SYSTEM, "summary": summ, "cost_usd_reported": cost, "rows": rows}, ensure_ascii=False, indent=1))
print(summ, "cost", round(cost, 4))
