#!/usr/bin/env python3
"""Read-only mechanical audit of hcmut_v1 and labour_vi_v1 (BENCHMARK-QA, 2026-10-23).

Only reads repository data; writes nothing except the JSON given with --out.
Usage: python3 evaluation/benchmarks/qa/audit_benchmarks.py --out evaluation/benchmarks/qa/audit_output_2026-10-23.json
"""
import argparse, collections, difflib, hashlib, json, math, re, sys, unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BENCHES = ["hcmut_v1", "labour_vi_v1"]
REQUIRED = ["task_id", "category", "question", "expected_behavior", "ground_truth_article_ids",
            "expected_answer", "reference_evidence", "doc_code", "gold_status", "verification"]
CATEGORIES = {"single", "multi", "out_of_scope"}
BEHAVIORS = {"answer", "refuse"}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def norm(s):
    return " ".join(unicodedata.normalize("NFC", s).split())


def fold(s):
    """lowercase, strip diacritics (for keyword search only)."""
    s = unicodedata.normalize("NFD", s.lower().replace("đ", "d"))
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def toks(s):
    return re.findall(r"\w+", fold(s))


NUM_RE = re.compile(r"\d[\d\.,]*\d|\d")


def numbers(s):
    out = set()
    for m in NUM_RE.findall(s):
        out.add(m.strip(".,"))
        out.add(re.sub(r"[\.,]", "", m))
    return out


def doc_prefix(doc_id):
    return re.split(r"_(?:Dieu|Phu|QD)", doc_id)[0]


def audit(bench):
    bdir = ROOT / "evaluation/benchmarks" / bench
    tasks = json.loads((bdir / "tasks.json").read_text())
    lock = json.loads((bdir / "benchmark.lock.json").read_text())
    corpus = json.loads((ROOT / lock["corpus"]["path"]).read_text())
    recs = {r["doc_id"]: r for r in corpus}
    ncontent = {k: norm(v["content"]) for k, v in recs.items()}
    res = {"benchmark": bench, "n_tasks": len(tasks), "checks": {}, "per_task": {}, "findings_mech": []}
    chk = res["checks"]

    def flag(tid, code, msg):
        res["findings_mech"].append({"task_id": tid, "code": code, "msg": msg})
        res["per_task"].setdefault(tid, []).append(code)

    # ---- lock hashes
    hashes = {}
    ok = True
    def h(label, path, expect):
        nonlocal ok
        got = sha(ROOT / path)
        hashes[label] = {"path": path, "expected": expect, "actual": got, "match": got == expect}
        ok &= got == expect
    h("tasks", lock["tasks"]["path"], lock["tasks"]["sha256"])
    h("corpus", lock["corpus"]["path"], lock["corpus"]["sha256"])
    h("profile", lock["profile"]["path"], lock["profile"]["sha256"])
    h("benchmark_yaml", lock["benchmark_yaml"]["path"], lock["benchmark_yaml"]["sha256"])
    for p, e in lock["verification_files"].items():
        h(p, p, e)
    chk["lock_hashes_match"] = {"pass": ok, "detail": hashes}
    ym = (bdir / "benchmark.yaml").read_text()
    m = re.search(r"^review_status:\s*([^\s#]+)", ym, re.M)
    chk["yaml_review_status_equals_lock"] = {"pass": (m.group(1) if m else None) == lock.get("review_status"), "yaml": m.group(1) if m else None, "lock": lock.get("review_status")}
    cnt_cat = collections.Counter(t["category"] for t in tasks)
    cnt_beh = collections.Counter(t["expected_behavior"] for t in tasks)
    chk["lock_counts_match"] = {"pass": dict(cnt_cat) == lock["tasks"]["categories"] and dict(cnt_beh) == lock["tasks"]["expected_behaviors"]
                                 and len(tasks) == lock["tasks"]["count"] and len(corpus) == lock["corpus"]["records"],
                                 "categories": dict(cnt_cat), "behaviors": dict(cnt_beh), "records": len(corpus)}

    # ---- schema
    ids = [t["task_id"] for t in tasks]
    chk["ids_unique"] = {"pass": len(ids) == len(set(ids))}
    missing = [(t["task_id"], f) for t in tasks for f in REQUIRED if f not in t]
    chk["required_fields"] = {"pass": not missing, "missing": missing}
    badcat = [(t["task_id"], t["category"]) for t in tasks if t["category"] not in CATEGORIES]
    badbeh = [(t["task_id"], t["expected_behavior"]) for t in tasks if t["expected_behavior"] not in BEHAVIORS]
    chk["category_values"] = {"pass": not badcat, "bad": badcat}
    chk["behavior_values"] = {"pass": not badbeh, "bad": badbeh}

    qdup = collections.Counter(norm(t["question"]) for t in tasks)
    chk["questions_unique"] = {"pass": all(v == 1 for v in qdup.values())}

    # ---- gold/evidence
    gold_missing, ev_mismatch, quote_fail, page_mismatch, coh = [], [], [], [], []
    n_quotes = 0
    quote_norm_only_nfc = 0
    for t in tasks:
        tid = t["task_id"]
        gold = t["ground_truth_article_ids"]
        for g in gold:
            if g not in recs:
                gold_missing.append((tid, g)); flag(tid, "GOLD_ID_MISSING", g)
        beh, cat = t["expected_behavior"], t["category"]
        if beh == "refuse" and (gold or t["reference_evidence"]):
            coh.append((tid, "refuse item has gold/evidence")); flag(tid, "REFUSE_HAS_GOLD", "")
        if beh == "answer" and not gold:
            coh.append((tid, "answer item without gold")); flag(tid, "ANSWER_NO_GOLD", "")
        if (cat == "out_of_scope") != (beh == "refuse"):
            coh.append((tid, "category/behaviour mismatch")); flag(tid, "CAT_BEH_MISMATCH", "")
        if cat == "single" and len(gold) != 1:
            coh.append((tid, f"single with {len(gold)} gold")); flag(tid, "SINGLE_GOLD_COUNT", str(len(gold)))
        if cat == "multi" and len(gold) < 2:
            coh.append((tid, "multi with <2 gold")); flag(tid, "MULTI_GOLD_COUNT", "")
        ev_ids = {e["article_id"] for e in t["reference_evidence"]}
        if ev_ids != set(gold):
            ev_mismatch.append((tid, sorted(ev_ids ^ set(gold)))); flag(tid, "EVIDENCE_ID_NE_GOLD", str(sorted(ev_ids ^ set(gold))))
        for e in t["reference_evidence"]:
            n_quotes += 1
            rec = recs.get(e["article_id"])
            if rec is None:
                continue
            q = norm(e["exact_quote"])
            if q not in ncontent[e["article_id"]]:
                quote_fail.append((tid, e["article_id"], e["exact_quote"][:80])); flag(tid, "QUOTE_NOT_VERBATIM", e["exact_quote"][:80])
            sp = rec.get("source_pages")
            sp = json.loads(sp) if isinstance(sp, str) else sp
            if e.get("pdf_pages") is not None and sp is not None and list(e["pdf_pages"]) != list(sp):
                page_mismatch.append((tid, e["article_id"], e["pdf_pages"], sp)); flag(tid, "PDF_PAGES_NE_SOURCE_PAGES", f"{e['pdf_pages']} vs {sp}")
    chk["gold_ids_exist"] = {"pass": not gold_missing, "missing": gold_missing}
    chk["evidence_ids_equal_gold"] = {"pass": not ev_mismatch, "mismatch": ev_mismatch}
    chk["category_behaviour_gold_coherence"] = {"pass": not coh, "issues": coh}
    chk["quotes_verbatim"] = {"pass": not quote_fail, "n_quotes": n_quotes, "failures": quote_fail}
    chk["pdf_pages_equal_source_pages"] = {"pass": not page_mismatch, "mismatch": page_mismatch}

    # doc_code consistency
    dc = []
    for t in tasks:
        if t["ground_truth_article_ids"]:
            first = recs.get(t["ground_truth_article_ids"][0])
            exp = first.get("doc_code") if first and first.get("doc_code") else (doc_prefix(t["ground_truth_article_ids"][0]).replace("HCMUT_", ""))
            if exp != t["doc_code"]:
                dc.append((t["task_id"], t["doc_code"], exp)); flag(t["task_id"], "DOC_CODE_MISMATCH", f"{t['doc_code']} vs {exp}")
    chk["doc_code_matches_first_gold"] = {"pass": not dc, "mismatch": dc}

    # ---- numeric grounding: numbers in expected_answer absent from evidence quotes / gold records
    numrep = []
    for t in tasks:
        if t["expected_behavior"] != "answer":
            continue
        ans_nums = numbers(t["expected_answer"]) - {"1", "2", "3", "4", "5"} if False else numbers(t["expected_answer"])
        ev_text = " ".join(e["exact_quote"] for e in t["reference_evidence"])
        rec_text = " ".join(recs[g]["content"] for g in t["ground_truth_article_ids"] if g in recs)
        ev_nums, rec_nums = numbers(ev_text), numbers(rec_text)
        not_in_ev = sorted(n for n in ans_nums if n not in ev_nums and len(n) >= 1)
        not_in_rec = sorted(n for n in ans_nums if n not in rec_nums)
        # also numbers the question gives away
        q_nums = numbers(t["question"])
        if not_in_ev:
            numrep.append({"task_id": t["task_id"], "answer_numbers_not_in_quotes": not_in_ev, "answer_numbers_not_in_gold_records": not_in_rec,
                           "note": "numbers may be derived (sum/product) or spelled out; manual review"})
    chk["answer_numbers_in_evidence"] = {"pass": None, "info": "heuristic; not a pass/fail", "flagged": numrep}

    # ---- leakage: share of answer content tokens (len>=4) that also appear in question
    leak = []
    for t in tasks:
        if t["expected_behavior"] != "answer":
            continue
        qa = set(toks(t["question"])); aa = [w for w in toks(t["expected_answer"]) if len(w) >= 4]
        if not aa:
            continue
        frac = sum(1 for w in aa if w in qa) / len(aa)
        leak.append((t["task_id"], round(frac, 2)))
    leak.sort(key=lambda x: -x[1])
    chk["answer_token_overlap_with_question_top10"] = {"pass": None, "info": "share of expected_answer tokens (len>=4) found in question; descriptive", "top": leak[:10]}

    # ---- near duplicates (token jaccard + SequenceMatcher)
    pairs = []
    for i in range(len(tasks)):
        for j in range(i + 1, len(tasks)):
            a, b = tasks[i], tasks[j]
            sa, sb = set(toks(a["question"])), set(toks(b["question"]))
            jac = len(sa & sb) / len(sa | sb)
            seq = difflib.SequenceMatcher(None, fold(a["question"]), fold(b["question"])).ratio()
            same_gold = bool(set(a["ground_truth_article_ids"]) & set(b["ground_truth_article_ids"]))
            if jac >= 0.45 or seq >= 0.6 or same_gold:
                pairs.append({"a": a["task_id"], "b": b["task_id"], "jaccard": round(jac, 2), "seq": round(seq, 2),
                              "shared_gold": sorted(set(a["ground_truth_article_ids"]) & set(b["ground_truth_article_ids"]))})
    pairs.sort(key=lambda p: -(p["jaccard"] + p["seq"]))
    chk["near_duplicate_or_shared_gold_pairs"] = {"pass": None, "info": "pairs with jaccard>=.45 or seq>=.6 or a shared gold record", "pairs": pairs}

    # ---- distributions
    by_doc = collections.Counter(t["doc_code"] for t in tasks)
    gold_by_doc = collections.Counter()
    for t in tasks:
        for g in t["ground_truth_article_ids"]:
            r = recs.get(g)
            gold_by_doc[(r.get("doc_code") if r and r.get("doc_code") else doc_prefix(g).replace("HCMUT_", ""))] += 1
    corpus_by_doc = collections.Counter(((r.get("doc_code") or doc_prefix(r["doc_id"]).replace("HCMUT_", ""))) for r in corpus)
    gold_unique = sorted({g for t in tasks for g in t["ground_truth_article_ids"]})
    res["distribution"] = {
        "category": dict(cnt_cat), "expected_behavior": dict(cnt_beh),
        "doc_code_field": dict(by_doc), "gold_records_by_doc": dict(gold_by_doc), "corpus_records_by_doc": dict(corpus_by_doc),
        "unique_gold_records": len(gold_unique), "corpus_records": len(corpus),
        "gold_records_used_by_more_than_one_task": {g: [t["task_id"] for t in tasks if g in t["ground_truth_article_ids"]]
                                                    for g in gold_unique if sum(g in t["ground_truth_article_ids"] for t in tasks) > 1},
        "gold_status": dict(collections.Counter(t["gold_status"] for t in tasks)),
        "answer_length_words_median": sorted(len(t["expected_answer"].split()) for t in tasks)[len(tasks)//2],
        "numeric_questions_by_answer_has_digit": sum(1 for t in tasks if t["expected_behavior"] == "answer" and re.search(r"\d", t["expected_answer"])),
    }
    # question-form patterns
    res["distribution"]["question_starts_with_explicit_law_reference"] = [
        t["task_id"] for t in tasks if re.search(r"(Điều\s+\d+|Quyết định\s+\d+|Nghị định|Thông tư|Bộ luật|Luật\s+\w+\s+\d{4}|\d+/\d{4}/)", t["question"])]

    # ---- sanity run signals (final runs)
    run_dir = {"hcmut_v1": "hcmut-sanity-final-v1", "labour_vi_v1": "labour-sanity-final-v1"}[bench]
    s = json.loads((ROOT / "evaluation/runs" / run_dir / "results.json").read_text())
    sig = {"run": run_dir, "summary": s["summary"], "closed_book_correct": [], "closed_book_partial": [], "oracle_not_correct": [], "oracle_errors": []}
    for r in s["rows"]:
        if r["expected_behavior"] == "answer":
            cv = (r["closed_book"].get("judgment") or {}).get("verdict")
            ov = (r["oracle"].get("judgment") or {}).get("verdict")
            if cv == "correct": sig["closed_book_correct"].append(r["task_id"])
            if cv == "partially_correct": sig["closed_book_partial"].append(r["task_id"])
            if ov != "correct": sig["oracle_not_correct"].append((r["task_id"], ov))
    sig["closed_book_answers_mentioning_HCMUT_scope"] = sum(
        1 for r in s["rows"] if re.search(r"Bách khoa|học vụ", (r["closed_book"].get("answer") or {}).get("content") or ""))
    sig["closed_book_answers_total"] = len(s["rows"])
    bs = (ROOT / "evaluation/benchmark_sanity.py").read_text()
    sig["sanity_script_closed_prompt_is_HCMUT_scoped"] = bool(re.search(r'CLOSED_SYSTEM\s*=\s*\("Trả lời ngắn gọn bằng tiếng Việt câu hỏi về quy định học vụ của Trường Đại học Bách khoa', bs))
    sig["sanity_oracle_refusal_context_is_titles_only"] = "the oracle context is the whole set of section titles" in bs
    res["sanity_run_signals"] = sig

    # ---- refusal keyword search: rank records by distinct-token overlap with the question and expected_answer-free question only
    ref = {}
    idf_df = collections.Counter()
    rec_tok = {k: set(toks(v["title"] + " " + v["content"])) for k, v in recs.items()}
    for ts in rec_tok.values():
        idf_df.update(ts)
    N = len(recs)
    stop = set(toks("là và của các có được theo trong cho một những khi này đó thì nếu bao nhiêu nào gì không về với tại từ để phải như hay hoặc"))
    for t in tasks:
        if t["expected_behavior"] != "refuse":
            continue
        qt = [w for w in set(toks(t["question"])) if w not in stop and len(w) > 1]
        scored = []
        for k, ts in rec_tok.items():
            sc = sum(math.log(N / (1 + idf_df[w])) for w in qt if w in ts)
            if sc > 0: scored.append((round(sc, 2), k))
        scored.sort(reverse=True)
        ref[t["task_id"]] = {"question": t["question"], "top_records_by_idf_overlap": scored[:6]}
    res["refusal_candidate_records"] = ref


    # ---- alternative support: quotes (or >=70% of their 6-grams) that also occur in NON-gold records
    def grams(tokens, n=6):
        return {tuple(tokens[i:i + n]) for i in range(max(0, len(tokens) - n + 1))}
    rec_tokens = {k: re.findall(r"\w+", unicodedata.normalize("NFC", v["content"]).lower()) for k, v in recs.items()}
    rec_grams = {k: grams(t) for k, t in rec_tokens.items()}
    alt = []
    for t in tasks:
        if t["expected_behavior"] != "answer":
            continue
        found = {}
        for e in t["reference_evidence"]:
            qt = re.findall(r"\w+", unicodedata.normalize("NFC", e["exact_quote"]).lower())
            qg = grams(qt)
            if len(qg) < 2:
                continue
            for k, g in rec_grams.items():
                if k in t["ground_truth_article_ids"]:
                    continue
                cov = len(qg & g) / len(qg)
                if cov >= 0.7:
                    found[k] = max(found.get(k, 0), round(cov, 2))
        if found:
            alt.append({"task_id": t["task_id"], "other_records_containing_quote_text": found})
            res["per_task"].setdefault(t["task_id"], []).append("ALT_SUPPORT_RECORD")
    chk["alternative_support_records_not_in_gold"] = {"pass": None, "info": "non-gold records containing >=70% of an evidence quote's 6-grams (possible equally valid citations / superseded duplicates)", "flagged": alt}

    # ---- evidence position inside long gold records (reranker window 1024 tokens ~ 3000 chars; dense engine cuts at 1500/3000 chars)
    pos = []
    for t in tasks:
        for e in t["reference_evidence"]:
            rec = recs.get(e["article_id"])
            if not rec:
                continue
            c = norm(rec["content"]); i = c.find(norm(e["exact_quote"]))
            if i > 3000:
                pos.append({"task_id": t["task_id"], "article_id": e["article_id"], "quote_offset_chars": i, "record_chars": len(c)})
    chk["evidence_beyond_first_3000_chars"] = {"pass": None, "info": "quote starts after char 3000 of its record", "flagged": pos}
    res["record_length_stats"] = {"gold_record_chars_max": max((len(norm(recs[g]["content"])) for t in tasks for g in t["ground_truth_article_ids"]), default=0),
                                  "corpus_chars_median": sorted(len(norm(r["content"])) for r in corpus)[len(corpus) // 2],
                                  "corpus_chars_max": max(len(norm(r["content"])) for r in corpus)}

    # ---- instrument-number pins: question names an instrument by number ("Nghị định 293/2025", "Quyết định 1260/QĐ-ĐHBK") that is absent from the gold record text
    pins = []
    for t in tasks:
        if t["expected_behavior"] != "answer":
            continue
        cited = re.findall(r"(?:Nghị định|Thông tư|Quyết định|Luật|Phụ lục)\s+(?:số\s+)?(\d{1,4})/(?:\d{4}|QĐ)", t["question"])
        if cited:
            txt = " ".join(recs[g]["content"] for g in t["ground_truth_article_ids"] if g in recs)
            if not any(re.search(r"\b" + c + r"/(?:\d{4}|QĐ)", txt) for c in cited):
                pins.append({"task_id": t["task_id"], "cited_numbers": cited})
    chk["questions_citing_instrument_number_absent_from_gold_text"] = {"pass": None, "info": "document pin lives only in metadata/doc_id, not in text that BM25 indexes (title+content)", "count": len(pins), "tasks": pins}

    # ---- lexical retrieval baseline (own BM25 over syllable unigrams, question text only; descriptive, NOT the system's retriever)
    docs = {k: re.findall(r"\w+", unicodedata.normalize("NFC", v["title"] + " " + v["content"]).lower()) for k, v in recs.items()}
    dfc = collections.Counter(w for d in docs.values() for w in set(d))
    avg = sum(len(d) for d in docs.values()) / len(docs)
    def bm25(qtoks, d, k1=1.5, b=0.75):
        tf = collections.Counter(d); sc = 0.0
        for w in set(qtoks):
            if w in tf:
                idf = math.log(1 + (len(docs) - dfc[w] + 0.5) / (dfc[w] + 0.5))
                sc += idf * tf[w] * (k1 + 1) / (tf[w] + k1 * (1 - b + b * len(d) / avg))
        return sc
    ranks = {}
    for t in tasks:
        if t["expected_behavior"] != "answer":
            continue
        q = re.findall(r"\w+", unicodedata.normalize("NFC", t["question"]).lower())
        order = sorted(docs, key=lambda k: -bm25(q, docs[k]))
        ranks[t["task_id"]] = min(order.index(g) + 1 for g in t["ground_truth_article_ids"])
    vals = sorted(ranks.values())
    res["bm25_gold_rank_baseline"] = {"n": len(vals), "top1": sum(v == 1 for v in vals), "top5": sum(v <= 5 for v in vals), "top10": sum(v <= 10 for v in vals),
                                      "median_rank": vals[len(vals) // 2], "worst": sorted(ranks.items(), key=lambda x: -x[1])[:8], "ranks": ranks}
    res["questions_naming_a_document_or_article"] = sum(1 for t in tasks if re.search(r"(Điều\s+\d+|Quyết định\s+\d+|Nghị định|Thông tư|Bộ luật|Luật\s+\w+\s+\d{4}|Phụ lục|Quy định|Quy chế|Nội quy)", t["question"]))

    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    out = {"generated_at": "2026-10-23 (+07)", "script": "evaluation/benchmarks/qa/audit_benchmarks.py", "results": {b: audit(b) for b in BENCHES}}
    txt = json.dumps(out, ensure_ascii=False, indent=1, default=str)
    if a.out:
        Path(a.out).write_text(txt)
    for b, r in out["results"].items():
        print(f"== {b}: {r['n_tasks']} tasks")
        for k, v in r["checks"].items():
            print(f"  {k:48s} {v['pass']}")
        print("  mech findings:", len(r["findings_mech"]))
        for f in r["findings_mech"][:40]:
            print("   -", f["task_id"], f["code"], f["msg"][:100])


if __name__ == "__main__":
    main()
