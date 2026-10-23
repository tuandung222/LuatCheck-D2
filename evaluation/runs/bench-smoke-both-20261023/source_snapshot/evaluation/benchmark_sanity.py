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

import requests

from evaluation.judge_gateway import local_environment

ANSWER_SYSTEM = ("Bạn trả lời câu hỏi về quy chế, quy định của trường đại học. Chỉ dùng TÀI LIỆU được cung cấp. "
                 "Nếu tài liệu không đủ để trả lời, nói rõ là không trả lời được từ tài liệu. Trả lời ngắn gọn bằng tiếng Việt.")
CLOSED_SYSTEM = ("Trả lời ngắn gọn bằng tiếng Việt câu hỏi về quy định học vụ của Trường Đại học Bách khoa - ĐHQG-HCM. "
                 "Nếu bạn không chắc, nói rõ là không biết.")
JUDGE_SYSTEM = ("You grade an answer against a reference answer for a Vietnamese university-regulation question. "
                "Return JSON only: {\"verdict\": \"correct\"|\"partially_correct\"|\"incorrect\"|\"appropriate_refusal\"|"
                "\"inappropriate_refusal\", \"reason\": \"<one sentence>\"}. If the expected behaviour is refuse, "
                "\"appropriate_refusal\" means the answer says the information is not available; answering with "
                "invented content is \"incorrect\". Judge meaning, not wording.")


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


def run_task(task, corpus, base, key, answer_model, judge_model):
    gold = [corpus[i] for i in task["ground_truth_article_ids"] if i in corpus]
    if task["expected_behavior"] == "refuse":
        # Out-of-scope items: give the records a retriever would plausibly return is out of scope here;
        # the oracle context is the whole set of section titles, so refusal is judged without leaking an answer.
        context = "\n".join(f"- {r['doc_id']}: {r['title']}" for r in corpus.values())
    else:
        context = "\n\n".join(f"[{r['doc_id']}] {r['content']}" for r in gold)
    out = {"task_id": task["task_id"], "category": task["category"], "expected_behavior": task["expected_behavior"]}
    for mode, messages in {
        "oracle": [{"role": "system", "content": ANSWER_SYSTEM},
                   {"role": "user", "content": f"TÀI LIỆU:\n{context}\n\nCÂU HỎI: {task['question']}"}],
        "closed_book": [{"role": "system", "content": CLOSED_SYSTEM},
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
                judge = chat(base, key, judge_model, [{"role": "system", "content": JUDGE_SYSTEM},
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
    parser.add_argument("--tasks", required=True)
    parser.add_argument("--corpus", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--answer-model", default="google/gemma-4-31b-it")
    parser.add_argument("--judge-model", default="deepseek/deepseek-v4-flash")
    parser.add_argument("--concurrency", type=int, default=4)
    args = parser.parse_args()
    env = local_environment()
    base, key = env["LUATCHECK_JUDGE_BASE_URL"].rstrip("/"), env["LUATCHECK_JUDGE_API_KEY"]
    tasks = json.loads(Path(args.tasks).read_text())
    corpus = {r["doc_id"]: r for r in json.loads(Path(args.corpus).read_text())}
    with ThreadPoolExecutor(args.concurrency) as pool:
        rows = list(pool.map(lambda t: run_task(t, corpus, base, key, args.answer_model, args.judge_model), tasks))
    summary = {}
    for mode in ("oracle", "closed_book"):
        verdicts = [((r[mode]["judgment"] or {}).get("verdict") or "error") for r in rows]
        summary[mode] = {v: verdicts.count(v) for v in sorted(set(verdicts))}
    result = {"answer_model": args.answer_model, "judge_model": args.judge_model, "tasks": args.tasks,
              "note": "LLM answers and LLM judgments; not human labels.", "summary": summary, "rows": rows}
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=1))
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
