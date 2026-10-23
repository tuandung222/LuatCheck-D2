#!/usr/bin/env python3
"""LLM second opinion on benchmark ground truth (BENCHMARK-QA, 2026-10-23).

Reads benchmark tasks + corpus, asks a gateway model whether each expected_answer follows from the
cited records. The output is an LLM OPINION ONLY; every flag must be verified against the corpus text.
The API key is read via evaluation.judge_gateway.local_environment and is never printed or written.
Usage (from repo root): python3 evaluation/benchmarks/qa/gateway_second_opinion.py --out <json> [--model M] [--budget-usd 0.7]
"""
import argparse, json, math, re, sys, time, unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from evaluation.judge_gateway import local_environment  # noqa: E402

BENCHES = {"hcmut_v1": "data/corpus/hcmut_academic_v1.json", "labour_vi_v1": "data/corpus/labour_vi_v1.json"}

SYS_ANSWER = """Bạn là chuyên gia rà soát bộ câu hỏi đáp có đáp án chuẩn (ground truth) cho văn bản quy phạm tiếng Việt.
Bạn được cho: một câu hỏi, đáp án tham chiếu (expected_answer) và NGUYÊN VĂN các bản ghi nguồn được coi là bằng chứng.
Chỉ dùng nguyên văn các bản ghi được cung cấp; KHÔNG dùng kiến thức bên ngoài để khẳng định điều gì là đúng/sai về pháp luật.
Hãy kiểm tra: (1) đáp án có suy ra trực tiếp và đầy đủ từ bản ghi không (số liệu, điều kiện, ngoại lệ, mốc thời gian, chủ thể)? (2) trong bản ghi có mệnh đề nào làm thay đổi/hạn chế đáp án mà đáp án bỏ sót không? (3) câu hỏi có mơ hồ (có >1 đáp án hợp lý), thiếu mốc thời gian/phạm vi áp dụng, hay đáp án đòi thêm thông tin ngoài bằng chứng không? (4) bằng chứng có đủ không hay cần thêm điều khoản khác?
Trả về DUY NHẤT một JSON: {"verdict": "correct|minor_issue|major_issue|incorrect", "issues": [{"type": "wrong_value|missing_condition|ambiguous_question|insufficient_evidence|time_frame|other", "detail": "...", "quote": "trích nguyên văn ngắn từ bản ghi (<=200 ký tự) hoặc null"}], "confidence": 0..1}. Nếu không có vấn đề, issues = [] và verdict = "correct". Không thêm lời giải thích ngoài JSON."""

SYS_REFUSE = """Bạn là chuyên gia rà soát bộ câu hỏi đáp. Câu hỏi dưới đây được gắn nhãn 'ngoài phạm vi kho văn bản' (đúng hành vi là từ chối vì kho không có thông tin).
Bạn được cho câu hỏi và các bản ghi nguồn có độ tương đồng từ khóa cao nhất với câu hỏi. Chỉ dựa vào nguyên văn các bản ghi này.
Hãy cho biết có bản ghi nào trả lời được câu hỏi (kể cả trả lời một phần, hay trả lời hợp lý bằng quy định khác) không.
Trả về DUY NHẤT một JSON: {"verdict": "unanswerable_confirmed|partially_answerable|answerable", "answering_records": [{"doc_id": "...", "quote": "trích nguyên văn (<=200 ký tự)", "why": "..."}], "confidence": 0..1}."""


def norm(s):
    return " ".join(unicodedata.normalize("NFC", s).split())


def fold(s):
    s = unicodedata.normalize("NFD", s.lower().replace("đ", "d"))
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def toks(s):
    return re.findall(r"\w+", fold(s))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--model", default="deepseek/deepseek-v4-pro")
    ap.add_argument("--budget-usd", type=float, default=0.7)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--max-record-chars", type=int, default=9000)
    a = ap.parse_args()
    env = local_environment()
    key, base = env.get("LUATCHECK_JUDGE_API_KEY", ""), env.get("LUATCHECK_JUDGE_BASE_URL", "")
    if not key or not base.startswith("https://"):
        sys.exit("gateway credential/endpoint not configured")

    jobs = []
    for b, cpath in BENCHES.items():
        tasks = json.loads((ROOT / f"evaluation/benchmarks/{b}/tasks.json").read_text())
        corpus = json.loads((ROOT / cpath).read_text())
        recs = {r["doc_id"]: r for r in corpus}
        df = {}
        rtok = {k: set(toks(v["title"] + " " + v["content"])) for k, v in recs.items()}
        for ts in rtok.values():
            for w in ts:
                df[w] = df.get(w, 0) + 1
        N = len(recs)
        stop = set(toks("là và của các có được theo trong cho một những khi này đó thì nếu bao nhiêu nào gì không về với tại từ để phải như hay hoặc"))
        for t in tasks:
            if t["expected_behavior"] == "answer":
                ctx = []
                for g in t["ground_truth_article_ids"]:
                    c = recs[g]["content"]
                    if len(c) > a.max_record_chars:  # keep windows around the quotes for very long records
                        keep, cn = [], norm(c)
                        for e in t["reference_evidence"]:
                            if e["article_id"] == g and norm(e["exact_quote"]) in cn:
                                i = cn.find(norm(e["exact_quote"]))
                                keep.append(cn[max(0, i - 2500): i + len(e["exact_quote"]) + 2500])
                        c = "\n[...]\n".join(dict.fromkeys(keep)) or cn[: a.max_record_chars]
                    ctx.append(f"### BẢN GHI {g} ({recs[g]['title'][:120]})\n{c}")
                user = (f"CÂU HỎI: {t['question']}\n\nĐÁP ÁN THAM CHIẾU (expected_answer): {t['expected_answer']}\n\n"
                        f"BẰNG CHỨNG THAM CHIẾU (trích dẫn): " + " || ".join(e["exact_quote"] for e in t["reference_evidence"]) +
                        "\n\nNGUYÊN VĂN CÁC BẢN GHI GOLD:\n" + "\n\n".join(ctx))
                jobs.append((b, t["task_id"], "answer", SYS_ANSWER, user))
            else:
                qt = [w for w in set(toks(t["question"])) if w not in stop and len(w) > 1]
                sc = sorted(((sum(math.log(N / (1 + df[w])) for w in qt if w in ts), k) for k, ts in rtok.items()), reverse=True)[:8]
                ctx = [f"### BẢN GHI {k} ({recs[k]['title'][:100]})\n{recs[k]['content'][:3500]}" for _, k in sc]
                user = f"CÂU HỎI: {t['question']}\n\nCÁC BẢN GHI GẦN NHẤT:\n" + "\n\n".join(ctx)
                jobs.append((b, t["task_id"], "refuse", SYS_REFUSE, user))
    if a.limit:
        jobs = jobs[: a.limit]

    spent = {"usd": 0.0}
    rows = []

    def run(job):
        b, tid, kind, sysm, user = job
        if spent["usd"] > a.budget_usd:
            return {"benchmark": b, "task_id": tid, "kind": kind, "status": "skipped_budget"}
        payload = {"model": a.model, "messages": [{"role": "system", "content": sysm}, {"role": "user", "content": user}],
                   "response_format": {"type": "json_object"}, "max_tokens": 6000, "temperature": 0}
        for attempt in range(3):
            try:
                r = requests.post(base.rstrip("/") + "/chat/completions", headers={"Authorization": "Bearer " + key},
                                  json=payload, timeout=240, allow_redirects=False)
                if r.status_code != 200:
                    raise RuntimeError(f"HTTP {r.status_code}")
                d = r.json()
                cost = (d.get("usage") or {}).get("cost")
                if cost is None:
                    cost = float(r.headers.get("x-litellm-response-cost", 0) or 0)
                spent["usd"] += float(cost or 0)
                txt = d["choices"][0]["message"]["content"]
                return {"benchmark": b, "task_id": tid, "kind": kind, "status": "ok", "model_returned": d.get("model"),
                        "cost_usd": cost, "usage": {k: v for k, v in (d.get("usage") or {}).items() if k in ("prompt_tokens", "completion_tokens", "total_tokens")},
                        "opinion": json.loads(txt)}
            except Exception as e:  # recorded, not hidden
                err = type(e).__name__ + ": " + str(e).replace(key, "***")[:200]
                time.sleep(2 * (attempt + 1))
        return {"benchmark": b, "task_id": tid, "kind": kind, "status": "error", "error": err}

    with ThreadPoolExecutor(max_workers=6) as pool:
        for f in as_completed([pool.submit(run, j) for j in jobs]):
            rows.append(f.result())
    rows.sort(key=lambda r: (r["benchmark"], r["task_id"]))
    out = {"note": "LLM opinion only; not ground truth. Verify every flag against corpus text.", "model": a.model,
           "total_cost_usd_reported": spent["usd"], "n": len(rows), "rows": rows}
    Path(a.out).write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print("done", len(rows), "cost", round(spent["usd"], 4), "ok", sum(r["status"] == "ok" for r in rows), "err", sum(r["status"] == "error" for r in rows))


if __name__ == "__main__":
    main()
