#!/usr/bin/env python3
"""Failure analysis of the frozen v3 main runs (read-only on data; recomputes retrieval with the real retriever).

Usage: python3 evaluation/probes/v3_failure_analysis.py <section> [...]
Sections: overview clarify queries repair tokens snippets refuse defects all
Everything is derived from evaluation/runs/d2-gpu-main-{hcmut,labour}-v3/trials.jsonl (ledger: request_messages,
responses, audit_events), evaluation/benchmarks/*/tasks.json, and (when present) judge/judgments.jsonl joined via
judge/private_mapping.json. Nothing is written except stdout.
"""
import json
import re
import statistics as st
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

RUNS = {"hcmut": ("d2-gpu-main-hcmut-v3", "hcmut_v1", "data/corpus/hcmut_academic_v1.json", "hcmut_academic"),
        "labour": ("d2-gpu-main-labour-v3", "labour_vi_v1", "data/corpus/labour_vi_v1.json", "labour_vi_multi")}
SYSTEM_VARIANTS = ("off", "l1", "l1_rerank")


# ----------------------------------------------------------------------------- loading
def load(bench):
    run, bname, corpus, profile = RUNS[bench]
    trials = [json.loads(l) for l in (ROOT / "evaluation/runs" / run / "trials.jsonl").read_text().splitlines() if l.strip()]
    tasks = {t["task_id"]: t for t in json.loads((ROOT / "evaluation/benchmarks" / bname / "tasks.json").read_text())}
    judg = {}
    jd = ROOT / "evaluation/runs" / run / "judge"
    mp = jd / "private_mapping.json"
    if mp.exists():
        mapping = {m["review_id"]: m for m in json.loads(mp.read_text())}
        raw = {}
        jp = jd / "judgments.jsonl"
        if jp.exists():                      # final judge output
            for line in jp.read_text().splitlines():
                if line.strip():
                    j = json.loads(line)
                    raw[j.get("review_id")] = j
        else:                                # judge still running: valid per-attempt judgments (provisional, read-only)
            for f in sorted((jd / "attempts").glob("*.json")):
                try:
                    a = json.loads(f.read_text())
                except json.JSONDecodeError:
                    continue
                if a.get("status") == "valid" and isinstance(a.get("judgment"), dict):
                    raw[a["review_id"]] = a["judgment"]
        for rid, j in raw.items():
            m = mapping.get(rid)
            if m:
                judg[(m["variant"], m["seed"], m["task_id"], m["attempt"])] = j
    return trials, tasks, judg


def key(t):
    return (t["variant"], t["seed"], t["task_id"], t["attempt"])


OBS = "[OBSERVATION_TOOL_RESULT]\n"


def steps(t):
    """List of dict(thought, action, args, out_tokens, outcome, next_user) per model call of a trial."""
    calls = t["ledger"]["llm_calls"]
    out = []
    for i, c in enumerate(calls):
        resp = c.get("response") or {}
        nxt = calls[i + 1]["request_messages"][-1]["content"] if i + 1 < len(calls) else None
        out.append({"thought": resp.get("thought", ""), "action": resp.get("action"), "args": resp.get("tool_args") or {},
                    "out_tokens": c.get("output_tokens"), "outcome": c.get("outcome"), "error": c.get("error"),
                    "error_kind": c.get("error_kind"), "next_user": nxt, "resp": resp,
                    "finish": (c.get("native_response") or {}).get("choices", [{}])[0].get("finish_reason")})
    return out


def obs_json(msg):
    if msg and msg.startswith(OBS):
        try:
            return json.loads(msg[len(OBS):])
        except json.JSONDecodeError:
            return None
    return None


def is_search(a):
    return a in ("search", "search_law")


def is_read(a):
    return a in ("read_document", "get_article", "read")


def correct(judg, t):
    j = judg.get(key(t))
    if not j:
        return None
    for f in ("correctness", "task_correct", "correct"):
        if f in j:
            return j[f]
    return None


def pct(a, b):
    return f"{a}/{b} ({100 * a / b:.0f}%)" if b else f"{a}/0"


def q(s, n=15):
    """<= n words of s (quote helper)."""
    w = str(s).replace("\n", " ").split()
    return " ".join(w[:n]) + (" ..." if len(w) > n else "")


def sys_trials(trials, variants=SYSTEM_VARIANTS):
    return [t for t in trials if t["kind"] == "system" and t["variant"] in variants]


# ----------------------------------------------------------------------------- overview
def overview():
    for bench in RUNS:
        trials, tasks, judg = load(bench)
        print(f"\n== {bench}: judge labels available: {len(judg)}")
        d = defaultdict(Counter)
        for t in trials:
            d[(t["variant"], t["expected_behavior"])][t["terminal_status"]] += 1
        for k in sorted(d):
            print(" ", k, dict(d[k]))


# ----------------------------------------------------------------------------- Q1 clarify
def clarify():
    for bench in RUNS:
        trials, tasks, judg = load(bench)
        print(f"\n===== CLARIFY {bench} =====")
        for variants, label in ((("off",), "off (no L1; cleanest controller behaviour)"), (("l1", "l1_rerank"), "l1+l1_rerank"),
                                (("oracle",), "oracle (gold given)")):
            ts = [t for t in trials if t["variant"] in variants]
            print(f"\n-- {label}")
            for eb in ("answer", "refuse"):
                sub = [t for t in ts if t["expected_behavior"] == eb]
                cl = [t for t in sub if t["terminal_status"] == "clarified"]
                print(f"  expected={eb}: clarified {pct(len(cl), len(sub))}")
            ans = [t for t in ts if t["expected_behavior"] == "answer"]
            cl = [t for t in ans if t["terminal_status"] == "clarified"]
            # position of clarify: number of tool calls and whether a read happened before it
            pos = Counter()
            for t in cl:
                s = steps(t)
                ns = sum(is_search(x["action"]) for x in s)
                nr = sum(is_read(x["action"]) for x in s)
                pos[(ns, nr)] += 1
            print("  (searches,reads) before clarify on answerable:", dict(sorted(pos.items())))
            # base rate of reading at all among non-clarify
            allpos = Counter()
            for t in ans:
                s = steps(t)
                allpos[(sum(is_search(x["action"]) for x in s), sum(is_read(x["action"]) for x in s), t["terminal_status"])] += 1
            tot_by_ns = Counter()
            cl_by_ns = Counter()
            for (ns, nr, ts_), n in allpos.items():
                tot_by_ns[ns] += n
                if ts_ == "clarified":
                    cl_by_ns[ns] += n
            print("  P(clarify | #searches at end):", {k: pct(cl_by_ns[k], tot_by_ns[k]) for k in sorted(tot_by_ns)})
            # did gold appear in retrieved set?
            hit = Counter()
            for t in cl:
                ret = set(t["ledger"]["retrieved_article_ids"])
                gold = set(t["gold_article_ids"])
                hit["gold_retrieved" if ret & gold else "gold_not_retrieved"] += 1
            print("  clarify on answerable: gold in retrieved set?", dict(hit))
            # clarify last-step type: does question ask for info already in the user question?
            first = Counter()
            for t in cl:
                s = steps(t)
                first[s[0]["action"]] += 1
            print("  first action of clarified trials:", dict(first))
        # examples
        print("\n-- examples (variant off, answerable): thought / question")
        ex = [t for t in trials if t["variant"] == "off" and t["expected_behavior"] == "answer" and t["terminal_status"] == "clarified"]
        for t in ex[:6]:
            s = steps(t)
            last = s[-1]
            print(f"  {t['task_id']} seed={t['seed']} #steps={len(s)} gold_ret={bool(set(t['ledger']['retrieved_article_ids']) & set(t['gold_article_ids']))}")
            print("    Q :", q(t["ledger"]["original_query"], 30))
            print("    TH:", q(last["thought"], 40))
            print("    CL:", q(last["args"].get("question"), 40))
        # classify the clarification question: asks for document content / generic / asks fact present in the question
        print("\n-- keyword classes of clarify questions (answerable, off)")
        cls = Counter()
        for t in ex:
            qq = str(steps(t)[-1]["args"].get("question", "")).lower()
            if re.search(r"văn bản|quyết định|điều|khoản|nội dung|quy chế|quy định|cung cấp thêm|cụ thể", qq):
                cls["asks_for_doc/section/specifics"] += 1
            elif re.search(r"khóa|ngành|chương trình|năm|loại|hình thức|trường hợp|hợp đồng", qq):
                cls["asks_for_situational_fact"] += 1
            else:
                cls["other"] += 1
        print(" ", dict(cls), "of", len(ex))


# ----------------------------------------------------------------------------- Q2 queries
def tokset(s):
    return set(re.findall(r"\w+", s.lower()))


def query_stats():
    from collections import OrderedDict
    from src.retrieval.hybrid_domain import HybridDomainRetriever
    from src.config.app_config import load_config
    for bench in RUNS:
        run, bname, corpus, profile = RUNS[bench]
        trials, tasks, judg = load(bench)
        print(f"\n===== QUERIES {bench} =====")
        mf = json.loads((ROOT / "evaluation/runs" / run / "manifest.json").read_text())
        retr = HybridDomainRetriever(corpus_path=str(ROOT / corpus), retrieval_mode="tfidf", rrf_k=60)

        def r_at(ids, gold, k):
            return len(set(ids[:k]) & set(gold)) / max(len(gold), 1)

        def hit_at(ids, gold, k):
            return float(bool(set(ids[:k]) & set(gold)))
        rows = []
        for t in sys_trials(trials, ("off", "l1")):
            if t["expected_behavior"] != "answer":
                continue
            s = steps(t)
            searches = [x for x in s if is_search(x["action"])]
            if not searches:
                continue
            first = str(searches[0]["args"].get("query") or "")
            question = t["ledger"]["original_query"]
            gold = t["gold_article_ids"]
            fr = [d.get("doc_id") or d.get("article_id") for d in retr.search(first, top_k=5)]
            qr = [d.get("doc_id") or d.get("article_id") for d in retr.search(question, top_k=5)]
            both = [d.get("doc_id") or d.get("article_id") for d in retr.search(question + " " + first, top_k=5)]
            # any-query union of what the agent actually retrieved
            union = t["ledger"]["retrieved_article_ids"]
            rows.append(dict(t=t, first=first, question=question, fr=fr, qr=qr, both=both, gold=gold, union=union,
                             n_search=len(searches)))
        n = len(rows)
        print(f"first-query trials (off+l1, answerable, >=1 search): {n}")
        for k in (1, 3, 5):
            print(f"  Recall@{k}: first model query {st.mean(r_at(r['fr'], r['gold'], k) for r in rows):.3f} | raw question "
                  f"{st.mean(r_at(r['qr'], r['gold'], k) for r in rows):.3f} | question+first query {st.mean(r_at(r['both'], r['gold'], k) for r in rows):.3f}")
        print(f"  Hit@5   : first query {st.mean(hit_at(r['fr'], r['gold'], 5) for r in rows):.3f} | raw question {st.mean(hit_at(r['qr'], r['gold'], 5) for r in rows):.3f}")
        # per-trial: gold in any retrieved (what the agent actually saw)
        print(f"  gold in agent's retrieved set (any search, top-k as asked): {pct(sum(bool(set(r['union']) & set(r['gold'])) for r in rows), n)}")
        # lengths and term overlap
        ql = [len(tokset(r["question"])) for r in rows]
        fl = [len(tokset(r["first"])) for r in rows]
        print(f"  token-set length: question mean {st.mean(ql):.1f} | first query mean {st.mean(fl):.1f}")
        ids_re = re.compile(r"\d+/[\w\-ĐĐ]+|\b\d+\.\d+\b|điều\s+\d+|khoản\s+\d+", re.I)
        qid = sum(bool(ids_re.search(r["question"])) for r in rows)
        kept = sum(bool(ids_re.search(r["question"])) and bool(ids_re.search(r["first"])) for r in rows)
        print(f"  questions with decision no./clause/article refs: {qid}; first query keeps any such ref: {kept}")
        # numbers (digits) in question that are dropped
        def nums(s):
            return set(re.findall(r"\d+(?:[./]\d+)*", s))
        qn = [(nums(r["question"]), nums(r["first"])) for r in rows]
        withnum = [(a, b) for a, b in qn if a]
        drop = sum(1 for a, b in withnum if a - b)
        print(f"  questions containing numbers: {len(withnum)}; first query drops >=1 of them: {drop}")
        # key term retention: fraction of question content tokens (idf-ish via df) kept
        corp = getattr(retr, "corpus", [])
        df = Counter(w for d in corp for w in tokset(d.get("content", "")))
        N = len(corp)
        import math
        def idf(w):
            return math.log((N + 1) / (df.get(w, 0) + 1))
        ret = []
        for r in rows:
            qt, ft = tokset(r["question"]), tokset(r["first"])
            tot = sum(idf(w) for w in qt)
            ret.append(sum(idf(w) for w in qt & ft) / tot if tot else 0)
        print(f"  IDF-weighted share of question terms kept in first query: mean {st.mean(ret):.2f}, median {st.median(ret):.2f}")
        # added generic terms
        added = Counter()
        for r in rows:
            for w in tokset(r["first"]) - tokset(r["question"]):
                added[w] += 1
        print("  most frequent terms the model ADDS to its first query:", added.most_common(12))
        # generic boilerplate prefix (source_name copied into the query)
        src = {"hcmut": "quy chế", "labour": "bộ luật"}[bench]
        print(f"  first queries containing '{src}': {pct(sum(src in r['first'].lower() for r in rows), n)}")
        # degenerate queries
        deg = [r for r in rows if len(tokset(r["first"])) <= 1 or r["first"].strip() in ("...", "")]
        print(f"  degenerate first queries (<=1 token or '...'): {len(deg)}", [r["first"] for r in deg][:5])
        # failing cases
        bad = [r for r in rows if not (set(r["fr"]) & set(r["gold"])) and (set(r["qr"]) & set(r["gold"]))]
        print(f"  first query misses gold@5 but raw question hits: {pct(len(bad), n)}")
        for r in bad[:4]:
            print("    Q:", q(r["question"], 25))
            print("    q1:", q(r["first"], 25))
        # same by variants and categories incl. multi
        for cat in ("single", "multi"):
            sub = [r for r in rows if r["t"]["category"] == cat]
            if sub:
                print(f"  [{cat}] n={len(sub)} R@5 first={st.mean(r_at(r['fr'], r['gold'], 5) for r in sub):.3f} question={st.mean(r_at(r['qr'], r['gold'], 5) for r in sub):.3f}")
        # what recorded retrieval said (trial metrics) for cross-check
        rec = [t["retrieval"]["Recall@5"] for t in sys_trials(trials, ("off",)) if t["expected_behavior"] == "answer" and t["retrieval"]]
        print(f"  recorded trial Recall@5 (off, all answerable incl. no-search): {st.mean(rec):.3f}")
        # outcome impact: terminal status vs whether first query hit
        o = defaultdict(Counter)
        for r in rows:
            h = bool(set(r["fr"]) & set(r["gold"]))
            o[h][r["t"]["terminal_status"]] += 1
        print("  terminal status by first-query-hit@5:", {k: dict(v) for k, v in o.items()})
        # clarify | gold retrieved?
        o2 = defaultdict(Counter)
        for r in rows:
            o2[bool(set(r["union"]) & set(r["gold"]))][r["t"]["terminal_status"]] += 1
        print("  terminal status by gold-in-retrieved-set:", {k: dict(v) for k, v in o2.items()})
        # multi-query: later queries
        later = Counter(r["n_search"] for r in rows)
        print("  #searches per trial:", dict(sorted(later.items())))


# ----------------------------------------------------------------------------- Q3 repair
def repair():
    for bench in RUNS:
        trials, tasks, judg = load(bench)
        print(f"\n===== REPAIR {bench} =====")
        ts = [t for t in sys_trials(trials, ("l1", "l1_rerank"))]
        react = Counter()
        fb_to_next = defaultdict(Counter)
        ex = defaultdict(list)
        n_rep = 0
        trials_with_rep = Counter()
        for t in ts:
            s = steps(t)
            for i, x in enumerate(s):
                nu = x["next_user"]
                if x["action"] == "answer" and nu and nu.startswith("CẢNH BÁO TỪ HỆ THỐNG"):
                    n_rep += 1
                    fb = re.search(r"vì các lý do sau:\n(.*?)\n\nYÊU CẦU", nu, re.S)
                    fbtxt = fb.group(1) if fb else nu
                    ftype = ("quote" if "Trích nguyên văn" in fbtxt else "unsupported_claims" if "chưa tìm thấy căn cứ" in fbtxt else
                             "unretrieved" if "chưa từng được bạn tra cứu" in fbtxt else "unknown_id" if "không tồn tại" in fbtxt else
                             "quantity" if re.search(r"số|con số|định lượng|quantity", fbtxt, re.I) else "other")
                    nxt = s[i + 1]["action"] if i + 1 < len(s) else "END(budget/terminal)"
                    nxt = "search" if is_search(nxt) else "read" if is_read(nxt) else nxt
                    fb_to_next[ftype][nxt] += 1
                    react[nxt] += 1
                    if len(ex[(ftype, nxt)]) < 2 and i + 1 < len(s):
                        ex[(ftype, nxt)].append((t["task_id"], q(fbtxt, 40), q(s[i + 1]["thought"], 40)))
        print(f"repair events: {n_rep}; model reaction to feedback: {dict(react)}")
        for ft, c in fb_to_next.items():
            print(f"  feedback={ft}: {dict(c)}")
        for k, v in ex.items():
            for e in v:
                print("   ex", k, e)
        # answerable tasks: number refusals after repair vs not
        ans = [t for t in ts if t["expected_behavior"] == "answer"]
        ref = [t for t in ans if t["terminal_status"] == "refused"]
        after = 0
        by_cat = Counter()
        for t in ref:
            nrep = t["ledger"]["repairs_count"]
            if nrep:
                after += 1
            by_cat["after_repair" if nrep else "no_repair"] += 1
            fo = t["ledger"]["final_output"] or {}
            r = fo.get("reason", "")
            if "tool" in r.lower() and "ngân sách" in r.lower():
                by_cat["budget_refusal"] += 1
            if "Không thể xác thực" in r:
                by_cat["repair_exhausted"] += 1
        print(f"refusals on answerable (l1,l1_rerank): {len(ref)} -> {dict(by_cat)}")
        # model's self-initiated refuse: how many cite 'snippet', 'không tìm thấy'
        why = Counter()
        for t in ref:
            fo = t["ledger"]["final_output"] or {}
            r = fo.get("reason", "").lower()
            if "không thể xác thực" in r:
                why["system:repair_exhausted"] += 1
            elif "snippet" in r or "đoạn trích" in r or "trích" in r:
                why["model:mentions_snippet/quote"] += 1
            elif "không tìm thấy" in r or "chưa" in r or "không có" in r:
                why["model:not_found"] += 1
            else:
                why["model:other"] += 1
        print("  refusal reasons on answerable:", dict(why))
        # answer attempts: first answer verified vs not. Repair success: after repair, next answer passes?
        succ = Counter()
        for t in ts:
            if t["ledger"]["repairs_count"]:
                succ[t["terminal_status"]] += 1
        print("  trials with >=1 repair -> final status:", dict(succ))
        # repair loops: after repair 1, does the model re-answer or give up
        # distribution of #repair per trial
        print("  repairs_count dist:", dict(Counter(t["ledger"]["repairs_count"] for t in ts)))


# ----------------------------------------------------------------------------- Q4 tokens
def tokens():
    for bench in RUNS:
        trials, tasks, judg = load(bench)
        print(f"\n===== TOKENS {bench} =====")
        allc = []
        for t in trials:
            if t["kind"] not in ("system",):
                continue
            for x in steps(t):
                allc.append((x, t))
        outs = [x["out_tokens"] for x, _ in allc if x["out_tokens"] is not None]
        outs.sort()
        def pc(p):
            return outs[min(len(outs) - 1, int(p * len(outs)))]
        print(f"model calls (system variants): {len(allc)}; output tokens mean {st.mean(outs):.0f} p50 {pc(.5)} p90 {pc(.9)} p99 {pc(.99)} max {outs[-1]}; >=900: {sum(o >= 900 for o in outs)}; ==1024: {sum(o >= 1024 for o in outs)}")
        # by action
        byact = defaultdict(list)
        thought_tok = []
        for x, t in allc:
            a = "search" if is_search(x["action"]) else "read" if is_read(x["action"]) else x["action"] or "ERR"
            if x["out_tokens"] is not None:
                byact[a].append(x["out_tokens"])
        for a, v in sorted(byact.items()):
            v.sort()
            print(f"  action {a}: n={len(v)} mean {st.mean(v):.0f} p90 {v[int(.9 * len(v))]} max {v[-1]}")
        # thought share: chars of thought vs rest
        th = [len(x["thought"]) for x, _ in allc if x["resp"]]
        tot = [len(json.dumps(x["resp"], ensure_ascii=False)) for x, _ in allc if x["resp"]]
        print(f"  thought chars mean {st.mean(th):.0f}, share of response chars {sum(th) / sum(tot):.2f}")
        # thought length by position in trial (do thoughts grow?)
        pos = defaultdict(list)
        for x, t in allc:
            pass
        # errors
        errs = [(x, t) for x, t in allc if x["outcome"] != "success"]
        print(f"  non-success calls: {len(errs)}: {Counter(x['error_kind'] for x, _ in errs)}")
        for x, t in errs:
            print(f"    {t['variant']} {t['task_id']} seed={t['seed']} out_tokens={x['out_tokens']} finish={x['finish']} err={x['error']} step#={t['ledger']['step_count']}")
        # trials with error: what was the call (use request message sizes)
        for t in trials:
            if t.get("terminal_status") == "error":
                c = t["ledger"]["llm_calls"][-1]
                nm = len(c["request_messages"])
                print(f"    error trial {t['variant']} {t['task_id']} s={t['seed']}: kind={t['error_kind']} last call msgs={nm} in_tok={c.get('input_tokens')} out_tok={c.get('output_tokens')}")
                raw = (c.get("native_response") or {}).get("choices", [{}])[0].get("message", {}).get("content", "")
                print("      raw tail:", repr(raw[-160:]), "| raw len", len(raw))
                # which field is long
                m = re.search(r'"action":\s*"(\w+)"', raw)
                print("      action in raw:", m.group(1) if m else None, "| thought chars:", len(re.findall(r'"thought":\s*"(.*?)(?<!\\)"', raw, re.S)[0]) if re.findall(r'"thought":\s*"(.*?)(?<!\\)"', raw, re.S) else None)
        # long answers: how often is out_tokens>600 and what action
        long = [(x, t) for x, t in allc if (x["out_tokens"] or 0) >= 600]
        print(f"  calls >=600 tokens: {len(long)} by action {Counter(x['action'] for x, _ in long)}")
        # repetition inside thought? crude: ratio unique trigram
        rep = 0
        for x, t in long:
            w = x["thought"].split()
            tri = list(zip(w, w[1:], w[2:]))
            if tri and len(set(tri)) / len(tri) < 0.6:
                rep += 1
        print(f"  of those, thought with repetitive trigrams (<0.6 unique): {rep}")
        # input tokens: the context used
        its = [c["input_tokens"] for t in trials if t["kind"] == "system" for c in t["ledger"]["llm_calls"] if c.get("input_tokens")]
        print(f"  input tokens: mean {st.mean(its):.0f} max {max(its)}")


# ----------------------------------------------------------------------------- Q5 snippets
def snippets():
    for bench in RUNS:
        trials, tasks, judg = load(bench)
        print(f"\n===== SNIPPETS {bench} =====")
        # build corpus lookup
        corpus = json.loads((ROOT / RUNS[bench][2]).read_text())
        docs = {(d.get("doc_id") or d.get("article_id")): d for d in (corpus if isinstance(corpus, list) else corpus.get("documents", corpus))}
        n_art = trunc = 0
        goldtot = goldsnip = goldfull = goldanswerinsnip = 0
        for t in sys_trials(trials, ("off",)):
            if t["expected_behavior"] != "answer":
                continue
            s = steps(t)
            gold = set(t["gold_article_ids"])
            task = tasks[t["task_id"]]
            seen_gold_snip = seen_gold_full = False
            for x in s:
                o = obs_json(x["next_user"])
                if not o:
                    continue
                for a in o.get("articles", []) or []:
                    n_art += 1
                    trunc += bool(a.get("snippet_truncated"))
                    if a["article_id"] in gold:
                        seen_gold_snip = True
                if o.get("status") == "success" and "full_content" in o and o.get("article_id") in gold:
                    seen_gold_full = True
            goldtot += 1
            goldsnip += seen_gold_snip
            goldfull += seen_gold_full
        print(f"articles shown in search results: {n_art}, snippet_truncated=true: {pct(trunc, n_art)}")
        print(f"answerable trials (off): gold seen as snippet in some search {pct(goldsnip, goldtot)}, gold read in full {pct(goldfull, goldtot)}")
        # for trials where gold snippet was seen: how often does the model read it before answering?
        beh = Counter()
        for t in sys_trials(trials, ("off",)):
            if t["expected_behavior"] != "answer":
                continue
            s = steps(t)
            gold = set(t["gold_article_ids"])
            saw = any((o := obs_json(x["next_user"])) and any(a["article_id"] in gold for a in (o.get("articles") or [])) for x in s)
            read_gold = any(is_read(x["action"]) and x["args"].get("article_id") in gold for x in s)
            beh[(saw, read_gold, t["terminal_status"])] += 1
        print("  (gold_in_snippet_seen, gold_read, terminal) counts:", dict(sorted(beh.items(), key=lambda kv: -kv[1])))
        # reference quote visible in snippet? (reference_evidence exact_quote tokens)
        vis = Counter()
        for t in sys_trials(trials, ("off",)):
            if t["expected_behavior"] != "answer" or t["category"] != "single":
                continue
            task = tasks[t["task_id"]]
            quotes = [re.sub(r"\s+", " ", e.get("exact_quote", "")).strip() for e in task.get("reference_evidence", [])]
            if not quotes:
                continue
            s = steps(t)
            snips = []
            for x in s:
                o = obs_json(x["next_user"])
                if o:
                    for a in o.get("articles", []) or []:
                        if a["article_id"] in set(task["ground_truth_article_ids"]):
                            snips.append(re.sub(r"\s+", " ", a["content_snippet"]))
            if not snips:
                vis["gold_not_shown"] += 1
            else:
                inside = any(qq[:60] in sn for qq in quotes for sn in snips)
                vis["gold_shown_ref_quote_start_in_snippet" if inside else "gold_shown_ref_quote_NOT_in_snippet"] += 1
        print("  gold evidence visibility in snippets (single, off):", dict(vis))
        # garbled table snippets: snippets with long digit runs
        garbled = 0
        tbl = 0
        for t in sys_trials(trials, ("off",)):
            for x in steps(t):
                o = obs_json(x["next_user"])
                if o:
                    for a in o.get("articles", []) or []:
                        sn = a["content_snippet"]
                        if re.search(r"(?:\b\d{1,2}\b\s+){3,}", sn):
                            garbled += 1
                        tbl += 1
        print(f"  snippet displays with >=3 consecutive bare small numbers (table-like): {garbled}/{tbl}")
        # titles truncated or starting with quote chars
        ti = Counter()
        for d in docs.values():
            tt = str(d.get("title") or d.get("section_title") or "")
            if tt.startswith(("“", '"')):
                ti["title starts with opening quote"] += 1
            if tt and not tt.rstrip().endswith((".", ")")) and len(tt) > 0 and tt[-1].islower():
                ti["title ends lowercase (maybe cut)"] += 1
        print("  corpus titles:", dict(ti), "of", len(docs))
        # read observations: complete? full_content chars vs corpus
        rd = Counter()
        for t in sys_trials(trials, ("off",)):
            for x in steps(t):
                if is_read(x["action"]):
                    o = obs_json(x["next_user"])
                    if o is None:
                        rd["no_obs"] += 1
                    elif o.get("status") == "success":
                        did = o["article_id"]
                        full = docs.get(did, {}).get("content", "")
                        rd["full_complete" if o.get("full_content") == full else "full_mismatch"] += 1
                    else:
                        rd["status_" + str(o.get("status"))] += 1
                        rd["err:" + str(x["args"].get("article_id"))[:40]] += 0
        print("  read observations:", dict(rd))
        # read of ids not exact? list wrong ids
        bad = Counter()
        for t in sys_trials(trials):
            for x in steps(t):
                if is_read(x["action"]):
                    o = obs_json(x["next_user"])
                    if o and o.get("status") != "success" and o.get("status") != "already_read":
                        bad[x["args"].get("article_id")] += 1
        print("  failed read ids (all system variants):", bad.most_common(8))
        # search-result duplicates, not_found
        st_c = Counter()
        for t in sys_trials(trials):
            for x in steps(t):
                if is_search(x["action"]):
                    o = obs_json(x["next_user"])
                    st_c[(o or {}).get("status", "none")] += 1
        print("  search statuses:", dict(st_c))


# ----------------------------------------------------------------------------- Q6 refuse tasks
def refuse():
    for bench in RUNS:
        trials, tasks, judg = load(bench)
        print(f"\n===== OUT-OF-SCOPE {bench} =====")
        oos = sorted({t["task_id"] for t in trials if t["expected_behavior"] == "refuse"})
        for tid in oos:
            print(f"\n{tid}: {q(tasks[tid]['question'], 22)}")
            for var in ("closed_book", "off", "l1", "l1_rerank"):
                ts = [t for t in trials if t["task_id"] == tid and t["variant"] == var]
                c = Counter(t["terminal_status"] for t in ts)
                print(f"   {var}: {dict(c)}")
            ex = [t for t in trials if t["task_id"] == tid and t["variant"] == "off" and t["terminal_status"] == "answered"]
            for t in ex[:1]:
                fo = t["ledger"]["final_output"]
                print("     off-answered content:", q(fo.get("content"), 35), "| cites", [c["article_id"] for c in fo.get("citations", [])])
            ex = [t for t in trials if t["task_id"] == tid and t["variant"] == "closed_book" and t["terminal_status"] == "answered"]
            for t in ex[:1]:
                fo = t["ledger"]["final_output"]
                print("     closed-book-answered:", q(fo.get("content"), 35))
            ex = [t for t in trials if t["task_id"] == tid and t["variant"] == "off" and t["terminal_status"] == "clarified"]
            for t in ex[:1]:
                s = steps(t)
                print("     off-clarified:", q(s[-1]["args"].get("question"), 30), "| #search", sum(is_search(x["action"]) for x in s))
        # across system variants: what share of refuse-task answers are cited retrieved docs, and relevance of queries
        ts = [t for t in sys_trials(trials) if t["expected_behavior"] == "refuse"]
        print(f"\nsystem refuse-task outcomes: {dict(Counter(t['terminal_status'] for t in ts))}")
        # answer-with-citations rate that passed L1
        ans = [t for t in ts if t["terminal_status"] == "answered"]
        print("  answered refuse-tasks:", len(ans), "verified by L1:", sum(1 for t in ans if (t['ledger']['final_output'] or {}).get('verified')))
        # did the clarify questions ask for info that would make the task answerable?
        for t in [t for t in ts if t["terminal_status"] == "clarified"][:5]:
            s = steps(t)
            print("   clarify ex", t["task_id"], t["variant"], "|", q(s[-1]["thought"], 30), "=>", q(s[-1]["args"].get("question"), 25))
        # how many searches before clarify on refuse tasks
        pos = Counter()
        for t in ts:
            if t["terminal_status"] == "clarified":
                pos[sum(is_search(x["action"]) for x in steps(t))] += 1
        print("  #searches before clarify on refuse tasks:", dict(pos))
        # top retrieved for refuse tasks: how many retrieved docs
        # guardrail refusals (pre-model)
        pm = [t for t in trials if t.get("pre_model_policy_refusal")]
        print(f"  pre-model policy refusals total: {len(pm)}", Counter((t["expected_behavior"], t["task_id"]) for t in pm).most_common(10))


# ----------------------------------------------------------------------------- Q7 other defects
def defects():
    from src.domains import load_profile
    for bench in RUNS:
        run, bname, corpus, profile = RUNS[bench]
        trials, tasks, judg = load(bench)
        prof = load_profile(profile)
        print(f"\n===== OTHER DEFECT SCAN {bench} =====")
        ts = sys_trials(trials)
        # budget handling
        bud = Counter()
        for t in ts:
            L = t["ledger"]
            fo = L["final_output"] or {}
            if t["terminal_status"] == "refused" and ("ngân sách" in str(fo.get("reason", "")).lower() or "giới hạn tối đa" in str(fo.get("reason", ""))):
                bud["system_budget_refusal"] += 1
                bud["by_expected:" + t["expected_behavior"]] += 1
            s = steps(t)
            if any(x["next_user"] and x["next_user"].startswith("[LỖI_NGÂN_SÁCH]") for x in s):
                bud["saw_budget_notice"] += 1
            if L["tool_calls_count"] >= 5:
                bud["used_all_5_tool_calls"] += 1
            if L["step_count"] >= 8:
                bud["used_all_8_steps"] += 1
        print("budget:", dict(bud))
        # duplicate / already_read
        dup = Counter()
        for t in ts:
            for x in steps(t):
                o = obs_json(x["next_user"])
                if o and o.get("status") in ("duplicate_query", "already_read"):
                    dup[o["status"]] += 1
                    dup["tool_call_consumed"] += 1
        print("notices (each consumes one tool call):", dict(dup))
        # steps consumed by repairs: tool budget vs step budget interplay
        # IDs: citation id normalisation. compare cited ids with retrieved ids
        idc = Counter()
        exs = []
        for t in ts:
            if t["terminal_status"] != "answered":
                continue
            fo = t["ledger"]["final_output"]
            ret = set(t["ledger"]["retrieved_article_ids"])
            for c in fo.get("citations", []):
                a = c["article_id"]
                if a in ret:
                    idc["exact_in_retrieved"] += 1
                elif a.lower().replace("đ", "d") in {r.lower() for r in ret}:
                    idc["case_or_diacritic_variant_only"] += 1
                else:
                    idc["not_retrieved"] += 1
                    if len(exs) < 3:
                        exs.append((t["task_id"], a))
        print("answered citation ids vs retrieved:", dict(idc), exs)
        # non-exact read ids that succeeded (normalisation in retriever)
        nrm = 0
        for t in ts:
            for x in steps(t):
                if is_read(x["action"]):
                    o = obs_json(x["next_user"])
                    if o and o.get("status") == "success" and o.get("article_id") != x["args"].get("article_id"):
                        nrm += 1
        print("reads where requested id != canonical id:", nrm)
        # citations to document with the wrong law_name ?
        # top_k usage
        tk = Counter()
        for t in ts:
            for x in steps(t):
                if is_search(x["action"]):
                    tk[x["args"].get("top_k", "absent")] += 1
        print("search top_k used:", dict(tk))
        # search action count per trial for answerable
        print("#searches per answerable trial (off):", dict(sorted(Counter(sum(is_search(x['action']) for x in steps(t)) for t in ts if t['variant'] == 'off' and t['expected_behavior'] == 'answer').items())))
        print("#reads per answerable trial (off):", dict(sorted(Counter(sum(is_read(x['action']) for x in steps(t)) for t in ts if t['variant'] == 'off' and t['expected_behavior'] == 'answer').items())))
        # premature answer from snippets with no read
        # answered without any read: share
        ans = [t for t in ts if t["variant"] == "off" and t["terminal_status"] == "answered" and t["expected_behavior"] == "answer"]
        nr = sum(1 for t in ans if not any(is_read(x["action"]) for x in steps(t)))
        print(f"off answered w/o any read: {pct(nr, len(ans))}")
        # guardrail false positives
        pm = [t for t in trials if t.get("pre_model_policy_refusal")]
        print("pre-model refusals:", [(t['variant'], t['task_id'], t['expected_behavior']) for t in pm][:10])
        # search_summary / empty query: "..." queries
        empt = 0
        for t in ts:
            for x in steps(t):
                if is_search(x["action"]) and len(tokset(str(x["args"].get("query", "")))) == 0:
                    empt += 1
        print("searches with token-less query (e.g. '...'):", empt)
        # model emits placeholder strings from the prompt ("từ khóa tìm kiếm", "...")
        ph = Counter()
        for t in ts:
            for x in steps(t):
                if is_search(x["action"]):
                    qq = str(x["args"].get("query", "")).strip().lower()
                    if qq in ("từ khóa tìm kiếm", "...", "từ khóa", "keyword"):
                        ph[qq] += 1
                if x["action"] == "answer":
                    for c in x["args"].get("citations", []) or []:
                        if isinstance(c, dict) and c.get("article_id") in ("HCMUT_QCDT_Dieu_12", "BLLD2019_Dieu_25"):
                            ph["cites_prompt_example_id"] += 1
        print("prompt-placeholder echoes:", dict(ph))


# ----------------------------------------------------------------------------- evidence in view / clarify
def _tok(s):
    return set(re.findall(r"\w+", s.lower()))


def evidence_view():
    """For single-evidence answerable tasks (variant off): is the reference evidence in the model's view (>=80% of the
    reference quote tokens in a shown snippet or a full read), and what does the controller do?"""
    for bench in RUNS:
        trials, tasks, judg = load(bench)
        print(f"\n===== EVIDENCE IN VIEW vs OUTCOME {bench} (variant off, single-category answerable) =====")
        c = Counter()
        read_c = Counter()
        for t in sys_trials(trials, ("off",)):
            if t["expected_behavior"] != "answer" or t["category"] != "single":
                continue
            task = tasks[t["task_id"]]
            gold = set(task["ground_truth_article_ids"])
            ev = {e["article_id"]: _tok(e["exact_quote"]) for e in task["reference_evidence"]}
            best = None
            did_read_gold = False
            for x in steps(t):
                o = obs_json(x["next_user"])
                if not o:
                    continue
                for a in o.get("articles") or []:
                    if a["article_id"] in gold:
                        cov = len(ev[a["article_id"]] & _tok(a["content_snippet"])) / max(len(ev[a["article_id"]]), 1)
                        best = max(best or 0, cov)
                if o.get("status") == "success" and o.get("article_id") in gold and "full_content" in o:
                    best, did_read_gold = 1.0, True
            cat = "gold_not_retrieved" if best is None else ("evidence_in_view" if best >= 0.8 else "retrieved_but_evidence_not_in_snippet")
            jc = correct(judg, t)
            c[(cat, t["terminal_status"])] += 1
            if t["terminal_status"] == "answered" and jc is not None:
                read_c[(cat, "judged_correct>=1" if jc >= 1 else "judged_wrong")] += 1
        for cat in ("gold_not_retrieved", "retrieved_but_evidence_not_in_snippet", "evidence_in_view"):
            row = {ts: c[(cat, ts)] for ts in ("answered", "clarified", "refused", "error") if c[(cat, ts)]}
            n = sum(row.values())
            print(f"  {cat}: n={n} {row} clarify share {row.get('clarified', 0) / max(n, 1):.2f}")
        if read_c:
            print("  judged (provisional) correctness of answered:", dict(read_c))
        # oracle floor
        orc = [t for t in trials if t["variant"] == "oracle" and t["expected_behavior"] == "answer"]
        print(f"  oracle (gold in context at step 0) clarify share: {sum(t['terminal_status'] == 'clarified' for t in orc)}/{len(orc)}")
        # reading behaviour
        reads = Counter()
        for t in sys_trials(trials, ("off",)):
            if t["expected_behavior"] == "answer":
                reads[sum(is_read(x["action"]) for x in steps(t))] += 1
        print("  #reads per answerable trial (off):", dict(sorted(reads.items())))


def judged():
    for bench in RUNS:
        trials, tasks, judg = load(bench)
        print(f"\n===== JUDGED (provisional per-attempt judgments, n={len(judg)}) {bench} =====")
        if not judg:
            print("  no judgments available")
            continue
        d = defaultdict(Counter)
        for t in trials:
            j = judg.get(key(t))
            if not j or not j.get("judgeable", True):
                continue
            d[(t["variant"], t["expected_behavior"], t["terminal_status"])][("c%s" % j.get("correctness"), "beh_ok" if j.get("behaviour_appropriate") else "beh_bad")] += 1
        for k in sorted(d):
            print(" ", k, dict(d[k]))
        # clarify on answerable
        n = sum(sum(v_.values()) for k, v_ in d.items() if k[1] == "answer" and k[2] == "clarified")
        print("  clarified on answerable (judged):", n)


# ----------------------------------------------------------------------------- extras (counterfactual retrieval, repair proxy, loops)
def extras():
    from src.retrieval.hybrid_domain import HybridDomainRetriever
    from src.tools.domain_tools import DomainKnowledgeRegistry
    from src.domains import load_profile
    num = lambda s: set(re.findall(r"\d+(?:[.,]\d+)?", s))
    for bench in RUNS:
        run, bname, corpus, prof = RUNS[bench]
        trials, tasks, judg = load(bench)
        print(f"\n===== EXTRAS {bench} =====")
        retr = HybridDomainRetriever(corpus_path=str(ROOT / corpus), retrieval_mode="tfidf", rrf_k=60)
        reg = DomainKnowledgeRegistry(retriever=retr, profile=load_profile(prof))
        ids = lambda qq, k: [d.get("doc_id") or d.get("article_id") for d in retr.search(qq, top_k=k)]
        rec = lambda lst, g, k: len(set(lst[:k]) & set(g)) / len(g)

        def rrf(lists, k, c=60):
            sc = {}
            for L in lists:
                for r, d in enumerate(L):
                    sc[d] = sc.get(d, 0) + 1 / (c + r + 1)
            return [d for d, _ in sorted(sc.items(), key=lambda kv: -kv[1])][:k]
        # (a) the retrieval seen by the controller really is top-3 (top_k never set by the model)
        tk = Counter(x["args"].get("top_k", "absent") for t in sys_trials(trials) for x in steps(t) if is_search(x["action"]))
        print("search top_k used by the model:", dict(tk), "-> loop default 3, final_top_k is 5")
        # (b) first-query retrieval under alternative constructions
        rows = []
        for t in sys_trials(trials, ("off", "l1")):
            if t["expected_behavior"] != "answer":
                continue
            ss = [x for x in steps(t) if is_search(x["action"])]
            if ss:
                rows.append((ss[0]["args"]["query"], tasks[t["task_id"]]["question"], t["gold_article_ids"]))
        for k in (1, 3, 5):
            print(f"  R@{k}: model {st.mean(rec(ids(m, k), g, k) for m, qq, g in rows):.3f} | question {st.mean(rec(ids(qq, k), g, k) for m, qq, g in rows):.3f}"
                  f" | RRF(q,model) {st.mean(rec(rrf([ids(qq, 20), ids(m, 20)], k), g, k) for m, qq, g in rows):.3f}"
                  f" | concat(question+model) {st.mean(rec(ids(qq + ' ' + m, k), g, k) for m, qq, g in rows):.3f}")
        # (c) evidence in view after the FIRST search, by construction (single tasks, variant off)
        tk_ = lambda s_: set(re.findall(r"\w+", s_.lower()))
        firsts = []
        for t in sys_trials(trials, ("off",)):
            if t["expected_behavior"] == "answer" and t["category"] == "single":
                ss = [x for x in steps(t) if is_search(x["action"])]
                if ss:
                    firsts.append((t["task_id"], ss[0]["args"]["query"]))

        def inview(tid, query, k, chars, cl):
            reg.SNIPPET_CHARS, reg.SNIPPET_CLAUSES = chars, cl
            task = tasks[tid]
            gold = set(task["ground_truth_article_ids"])
            ev = {e["article_id"]: tk_(e["exact_quote"]) for e in task["reference_evidence"]}
            for a in reg.search_knowledge(query, top_k=k).get("articles", []):
                if a["article_id"] in gold and len(ev[a["article_id"]] & tk_(a["content_snippet"])) / max(len(ev[a["article_id"]]), 1) >= 0.8:
                    return True
            return False
        print(f"  P(reference evidence >=80% token-covered in the first search result), n={len(firsts)}:")
        for lab, qsel, k, ch, cl in [("model query, top3, 600/2 (as run)", "m", 3, 600, 2), ("model query, top5, 600/2", "m", 5, 600, 2),
                                     ("question, top3, 600/2", "q", 3, 600, 2), ("question, top5, 600/2", "q", 5, 600, 2),
                                     ("question, top3, 1000/3", "q", 3, 1000, 3), ("question, top5, 1000/3", "q", 5, 1000, 3)]:
            print(f"    {lab}: {st.mean(inview(tid, tasks[tid]['question'] if qsel == 'q' else mq, k, ch, cl) for tid, mq in firsts):.3f}")
        # (d) recovery after a first-search miss
        c = Counter()
        gold_of = lambda t: set(t["gold_article_ids"])
        for t in sys_trials(trials, ("off", "l1")):
            if t["expected_behavior"] != "answer":
                continue
            seen = []
            for x in steps(t):
                o = obs_json(x["next_user"])
                if is_search(x["action"]) and o and o.get("articles") is not None:
                    seen.append(bool({a["article_id"] for a in o["articles"]} & gold_of(t)))
            if not seen:
                continue
            c["first_hit" if seen[0] else "first_miss"] += 1
            if not seen[0] and len(seen) > 1:
                c["miss_then_researched"] += 1
                c["recovered"] += any(seen[1:])
        print("  first-search hit/miss and recovery:", dict(c))
        # (e) clarify questions: generic request for details or echo of the user's question (keyword heuristic)
        ex = [t for t in sys_trials(trials) if t["expected_behavior"] == "answer" and t["terminal_status"] == "clarified"]
        more = echo = either = 0
        for t in ex:
            qq = str(steps(t)[-1]["args"].get("question", "")).lower()
            uq = set(re.findall(r"\w+", t["ledger"]["original_query"].lower()))
            qt = re.findall(r"\w+", qq)
            e = sum(w in uq for w in qt) / max(len(qt), 1) >= 0.5
            m = bool(re.search(r"cung cấp thêm|bổ sung|chi tiết hơn|thêm thông tin|bạn có thể|vui lòng|cần thông tin|cần biết|cho biết|làm rõ", qq))
            echo += e
            more += m
            either += (e or m)
        print(f"  clarify on answerable (all system variants) n={len(ex)}: generic 'more details' phrase {more}, echoes the question {echo}, either {either}")
        # (f) searches=0 terminal
        z = Counter((t["expected_behavior"], t["terminal_status"]) for t in sys_trials(trials) if not any(is_search(x["action"]) for x in steps(t)))
        print(f"  system trials with zero searches: {sum(z.values())}/{len(sys_trials(trials))}", dict(z))
        # (g) duplicate-query loops
        nxt = Counter()
        for t in sys_trials(trials):
            ss = steps(t)
            for i, x in enumerate(ss):
                o = obs_json(x["next_user"])
                if o and o.get("status") == "duplicate_query":
                    n = ss[i + 1]["action"] if i + 1 < len(ss) else "END"
                    nxt["search" if is_search(n) else "read" if is_read(n) else n] += 1
        print("  action right after a duplicate_query notice:", dict(nxt))
        # (h) repair: first rejected answer vs gold (structural proxy, not correctness)
        c = Counter()
        for t in sys_trials(trials, ("l1", "l1_rerank")):
            if t["expected_behavior"] != "answer":
                continue
            ss = steps(t)
            first = next((x for x in ss if x["action"] == "answer"), None)
            if not first or not first["next_user"] or not first["next_user"].startswith("CẢNH BÁO"):
                continue
            task = tasks[t["task_id"]]
            cites = [ci.get("article_id") for ci in first["args"].get("citations", []) if isinstance(ci, dict)]
            cg = bool(set(cites) & set(task["ground_truth_article_ids"]))
            en = num(task["expected_answer"])
            numok = (not en) or en <= num(first["args"].get("content", ""))
            c[("final=" + t["terminal_status"], cg, numok)] += 1
        tot = sum(c.values())
        ref = sum(v_ for k, v_ in c.items() if k[0] == "final=refused")
        print(f"  first answer rejected by L1: {tot}; of the {ref} that ended refused: cited a gold article {sum(v_ for k, v_ in c.items() if k[0] == 'final=refused' and k[1])},"
              f" gold cited AND all expected-answer numbers present {sum(v_ for k, v_ in c.items() if k[0] == 'final=refused' and k[1] and k[2])}")
        # (i) re-answer after quote-mismatch feedback
        c = Counter()
        th = 0
        n_after = 0
        for t in sys_trials(trials, ("l1", "l1_rerank")):
            ss = steps(t)
            for i, x in enumerate(ss):
                if x["action"] == "answer" and x["next_user"] and x["next_user"].startswith("CẢNH BÁO") and "Trích nguyên văn" in x["next_user"] and i + 1 < len(ss):
                    y = ss[i + 1]
                    n_after += 1
                    th += y["thought"].lstrip().lower().startswith("người dùng")
                    if y["action"] == "answer":
                        q2 = [ci.get("exact_quote") for ci in y["args"].get("citations", []) if isinstance(ci, dict)]
                        done = (i + 2 >= len(ss)) and t["terminal_status"] == "answered"
                        c[("quotes dropped" if not any(q2) else "quotes kept/rewritten", "passed" if done else "failed/continued")] += 1
        print(f"  after quote-mismatch feedback (n={n_after}): thought begins 'Người dùng' {th}; re-answers {dict(c)}")
        # (j) controller-made refusals
        src = Counter()
        for t in sys_trials(trials):
            fo = t["ledger"]["final_output"] or {}
            if t["terminal_status"] == "refused":
                r = str(fo.get("reason", ""))
                src["controller:repair_exhausted" if r.startswith("Không thể xác thực") else
                    "controller:budget" if ("giới hạn tối đa" in r or "ngân sách" in r.lower()) else "model/guardrail"] += 1
        print("  refused trials by source (system variants):", dict(src))


SECTIONS = {"overview": overview, "clarify": clarify, "queries": query_stats, "repair": repair, "tokens": tokens,
            "snippets": snippets, "refuse": refuse, "defects": defects, "evidence": evidence_view, "judged": judged, "extras": extras}

if __name__ == "__main__":
    args = sys.argv[1:] or ["all"]
    for a in (SECTIONS if "all" in args else args):
        SECTIONS[a]()
