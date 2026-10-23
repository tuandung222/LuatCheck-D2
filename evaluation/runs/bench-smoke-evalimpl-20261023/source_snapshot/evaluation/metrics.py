"""
Evaluation Metrics for LuatCheck Benchmark.
Calculates quantitative metrics conforming to Kapoor et al. (TMLR 2025) & Gao et al. (ALCE 2023).
"""
import re
import numpy as np
from typing import List, Dict, Any, Set, Optional

from src.agent.state import Citation


def normalize_id(aid: str) -> str:
    aid = aid.strip().lower().replace(" ", "_")
    if aid.startswith("điều_"):
        aid = "dieu_" + aid[5:]
    return aid


def calculate_retrieval_metrics(retrieved_ids: List[str], ground_truth_id: Any, k_list: List[int] = [1, 3, 5]) -> Dict[str, float]:
    """
    Computes Recall@k and MRR for statutory retrieval tasks.
    """
    if isinstance(ground_truth_id, (list, tuple, set)):
        norm_gts = [normalize_id(g) for g in ground_truth_id if g]
    else:
        norm_gts = [normalize_id(ground_truth_id)] if ground_truth_id else []

    # Rank positions are over *distinct* documents in first-appearance order; a repeated id must not push others down.
    norm_retrieved = list(dict.fromkeys(normalize_id(r) for r in retrieved_ids if r))

    metrics = {}
    for k in k_list:
        hit_count = len(set(norm_gts) & set(norm_retrieved[:k]))
        metrics[f"Recall@{k}"] = hit_count / len(set(norm_gts)) if norm_gts else 0.0
        metrics[f"Hit@{k}"] = float(hit_count > 0)

    # MRR (Mean Reciprocal Rank)
    ranks = [norm_retrieved.index(g) + 1 for g in norm_gts if g in norm_retrieved]
    if ranks:
        metrics["MRR"] = round(1.0 / min(ranks), 4)
    else:
        metrics["MRR"] = 0.0
    metrics["nDCG@5"] = round(ndcg_at_k(norm_retrieved, norm_gts, 5), 4)

    return metrics


def ndcg_at_k(ranked: List[str], gold: Any, k: int) -> float:
    """Binary-relevance nDCG@k over distinct ranked ids (relevant = gold id). 0.0 when there is no gold id."""
    gold_set = set(gold)
    if not gold_set:
        return 0.0
    seen = list(dict.fromkeys(ranked))[:k]
    dcg = sum(1.0 / np.log2(i + 2) for i, doc in enumerate(seen) if doc in gold_set)
    ideal = sum(1.0 / np.log2(i + 2) for i in range(min(len(gold_set), k)))
    return float(dcg / ideal) if ideal else 0.0


def calculate_citation_metrics(predicted_citations: List[str], ground_truth_id: Any) -> Dict[str, float]:
    """
    Legacy per-trial citation precision/recall (kept for run_eval.py and for rows recorded before the benchmark
    analysis recomputed these from the ledger). Quirks, by design of the original definition: nothing cited ->
    precision 0.0 (not undefined); no gold id but something cited -> recall 1.0 (vacuous). The benchmark analysis does
    NOT use this function; it uses trial_citation_metrics below (precision undefined when nothing is cited, plus F1).
    Source-ID set match only: it says nothing about whether the answer text is correct.
    """
    if isinstance(ground_truth_id, (list, tuple, set)):
        norm_gts = {normalize_id(g) for g in ground_truth_id if g}
    else:
        norm_gts = {normalize_id(ground_truth_id)} if ground_truth_id else set()

    norm_preds = {normalize_id(c) for c in predicted_citations if c}

    if not norm_preds:
        return {"citation_precision": 0.0, "citation_recall": 0.0, "citation_f1": 0.0}
    if not norm_gts:
        return {"citation_precision": 0.0, "citation_recall": 1.0, "citation_f1": 0.0}

    hits = len(norm_preds & norm_gts)
    precision = hits / len(norm_preds) if norm_preds else 0.0
    recall = hits / len(norm_gts) if norm_gts else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return {
        "citation_precision": round(float(precision), 4),
        "citation_recall": round(float(recall), 4),
        "citation_f1": round(float(f1), 4),
    }


def calculate_latency_percentiles(latencies: List[float]) -> Dict[str, float]:
    """
    Computes p50 and p95 latency (in milliseconds).
    """
    if not latencies:
        return {"p50_ms": 0.0, "p95_ms": 0.0}
    return {
        "p50_ms": round(float(np.percentile(latencies, 50)), 2),
        "p95_ms": round(float(np.percentile(latencies, 95)), 2)
    }


def calculate_unsupported_rate(
    answer_text: Optional[str],
    cited_articles: Optional[List[Any]],
    verifier: Any,
    retrieved_article_ids: Optional[List[str]] = None
) -> float:
    """
    Computes Unsupported-Sentence Rate (fraction of claims lacking statutory support).
    Lexical/provenance proxy only; not an independent semantic-correctness score:
    - If answer is empty or a refusal, Unsupported Rate = 0.0 (no unsupported assertions made).
    - Splits the response into individual proposition sentences.
    - Matches each sentence against cited statutory articles using the verifier.
    - Unsupported Rate = unsupported sentences / total proposition sentences.
    """
    if not answer_text or not isinstance(answer_text, str) or not answer_text.strip():
        return 0.0

    # 1. Split response into individual proposition sentences
    raw_sentences = [s.strip() for s in re.split(r'[.?!]\s+|\n+', answer_text) if s.strip()]
    sentences = []
    for s in raw_sentences:
        cleaned = re.sub(r'^[-\s•*0-9.)]+', '', s).strip()
        # Filter out short fragments or titles that lack legal propositions
        if len(cleaned) > 15:
            sentences.append(cleaned)

    # If no sentence > 15 chars but text is non-empty, keep full text
    if not sentences and len(answer_text.strip()) > 0:
        sentences = [answer_text.strip()]

    if not sentences:
        return 0.0

    # 2. Normalize list of cited statutory articles
    citation_objs = []
    raw_article_ids = []
    if cited_articles:
        for c in cited_articles:
            if isinstance(c, Citation):
                citation_objs.append(c)
                raw_article_ids.append(c.article_id)
            elif isinstance(c, dict) and "article_id" in c:
                citation_objs.append(Citation(article_id=str(c["article_id"])))
                raw_article_ids.append(str(c["article_id"]))
            elif isinstance(c, str) and c.strip():
                citation_objs.append(Citation(article_id=c.strip()))
                raw_article_ids.append(c.strip())

    # If an affirmative response is provided without any statutory citations
    if not citation_objs:
        return 1.0

    if retrieved_article_ids is None:
        retrieved_article_ids = list(raw_article_ids)

    # 3. Verify each sentence using verifier
    unsupported_count = 0
    for s in sentences:
        is_supported = False
        if hasattr(verifier, "verify"):
            res = verifier.verify(
                answer_text=s,
                citations=citation_objs,
                retrieved_article_ids=retrieved_article_ids
            )
            is_supported = getattr(res, "is_valid", False)
        elif hasattr(verifier, "verify_all_claims"):
            res = verifier.verify_all_claims(s, raw_article_ids)
            is_supported = res.get("is_entailed", False)
        elif hasattr(verifier, "verify_entailment"):
            for aid in raw_article_ids:
                is_ent, _, _ = verifier.verify_entailment(s, aid)
                if is_ent:
                    is_supported = True
                    break
        else:
            raise TypeError("A supported verifier interface is required; unsupported claims cannot default to valid.")

        if not is_supported:
            unsupported_count += 1

    return round(float(unsupported_count / len(sentences)), 4)



# =============================================================================================================
# Benchmark-run metrics (D2). Everything below is a pure function of recorded trial rows (evaluation/run_benchmark.py)
# and the frozen task's gold ids. Gold ids are read only AFTER the trial finished; the agent never sees them.
# Lexical/ID-set quantities are proxies for retrieval and citation quality, not answer correctness.
# =============================================================================================================

STATUSES = ("answered", "refused", "clarified", "error")
EXPECTED = ("answer", "refuse")


def _distinct_norm(ids: Any) -> List[str]:
    return list(dict.fromkeys(normalize_id(str(i)) for i in (ids or []) if i))


def trace_from_ledger(ledger: Dict[str, Any]) -> Dict[str, Any]:
    """The agent's retrieval trace from a recorded ledger (dict): distinct ids surfaced by searches and reads in
    first-appearance order (search hits in the order the tool returned them, then ids added by reads), the ids it asked to
    read, and per-search reranker metadata when present. Tool names are domain-specific; searches/reads are told apart
    by their canonical argument (`query` vs `article_id`)."""
    surfaced = _distinct_norm(ledger.get("retrieved_article_ids"))
    reads, searches, rerank = [], 0, []
    for event in ledger.get("audit_events") or []:
        if event.get("event") != "tool_call":
            continue
        args = event.get("args") or {}
        if "article_id" in args:
            reads.append(normalize_id(str(args["article_id"])))
        elif "query" in args:
            searches += 1
            meta = (event.get("metadata") or {}).get("rerank")
            if meta:
                rerank.append(meta)
    return {"surfaced": surfaced, "read_requested": list(dict.fromkeys(reads)), "n_searches": searches, "rerank": rerank}


def trial_retrieval_metrics(ledger: Dict[str, Any], gold_ids: Any) -> Dict[str, Any]:
    """Retrieval of gold ids over the search+read trace of one trial (defined only for trials with gold ids).

    Recall@k / Hit@k / nDCG@5: over the first k distinct ids of the trace. MRR: reciprocal rank of the first gold id.
    trace_recall: share of gold ids surfaced anywhere in the trace (Recall@infinity). read_recall: share of gold ids
    the agent explicitly read and that were returned (reads only add an id when the tool succeeded).
    NOTE the trace concatenates the results of successive searches, so k counts distinct documents across the whole
    trajectory, not the rank inside a single search result list.
    """
    gold = _distinct_norm(gold_ids)
    trace = trace_from_ledger(ledger)
    base = calculate_retrieval_metrics(trace["surfaced"], gold)
    out = {k: v for k, v in base.items()}
    surfaced, read = set(trace["surfaced"]), set(trace["read_requested"]) & set(trace["surfaced"])
    out["trace_recall"] = len(set(gold) & surfaced) / len(gold) if gold else None
    out["read_recall"] = len(set(gold) & read) / len(gold) if gold else None
    out["n_surfaced"], out["n_searches"], out["n_reads"] = len(trace["surfaced"]), trace["n_searches"], len(trace["read_requested"])
    if trace["rerank"] and gold:
        first_stage = set(normalize_id(i) for m in trace["rerank"] for i in (m.get("first_stage_ids") or []) if i)
        returned = set(normalize_id(i) for m in trace["rerank"] for i in (m.get("reranked_ids") or []) if i)
        out["rerank_first_stage_gold_recall"] = len(set(gold) & first_stage) / len(gold)
        out["rerank_returned_gold_recall"] = len(set(gold) & returned) / len(gold)
    return out


def trial_citation_metrics(final_output: Optional[Dict[str, Any]], ledger: Dict[str, Any], gold_ids: Any) -> Dict[str, Any]:
    """Citation-ID quality of the final answer against gold ids (source-ID set match; not answer correctness).

    precision: cited-and-gold / cited; None when nothing is cited (undefined, not zero). recall: cited-and-gold / gold.
    f1: harmonic mean, 0.0 when nothing matches. cited_not_retrieved: cited ids the agent never surfaced in its own
    trace (a gold-free groundedness check: the agent cited a document it did not see).
    """
    final = final_output or {}
    cited = _distinct_norm(c.get("article_id") for c in (final.get("citations") or []) if isinstance(c, dict))
    gold = set(_distinct_norm(gold_ids))
    surfaced = set(trace_from_ledger(ledger)["surfaced"])
    hits = len(set(cited) & gold)
    precision = hits / len(cited) if cited else None
    recall = hits / len(gold) if gold else None
    if recall is None:
        f1 = None
    elif precision is None or (precision + recall) == 0:
        f1 = 0.0
    else:
        f1 = 2 * precision * recall / (precision + recall)
    return {"cited_n": len(cited), "hits": hits, "gold_n": len(gold), "precision": precision, "recall": recall, "f1": f1,
            "cited_not_retrieved": len([c for c in cited if c not in surfaced])}


def _mean(values: List[float]) -> Optional[float]:
    return float(np.mean(values)) if values else None


def aggregate_retrieval(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Mean retrieval metrics over answerable trials (gold ids present). Execution-error trials stay in the average with
    the trace they produced (usually empty): an error is a failure to retrieve. `non_error_*` repeats the key values
    without them so the effect of errors is visible."""
    answerable = [r for r in rows if r.get("gold_article_ids")]
    per = [trial_retrieval_metrics(r["ledger"], r["gold_article_ids"]) for r in answerable]
    keys = ["Recall@1", "Recall@3", "Recall@5", "Hit@5", "MRR", "nDCG@5", "trace_recall", "read_recall"]
    out: Dict[str, Any] = {"answerable_trials": len(answerable)}
    for key in keys:
        out[key] = _mean([m[key] for m in per if m.get(key) is not None])
    clean = [m for m, r in zip(per, answerable) if not r["system_error"]]
    out["non_error_trials"] = len(clean)
    for key in ("Recall@5", "MRR", "trace_recall"):
        out[f"non_error_{key}"] = _mean([m[key] for m in clean])
    rerank = [m for m in per if "rerank_first_stage_gold_recall" in m]
    out["rerank_trials"] = len(rerank)
    out["rerank_first_stage_gold_recall"] = _mean([m["rerank_first_stage_gold_recall"] for m in rerank])
    out["rerank_returned_gold_recall"] = _mean([m["rerank_returned_gold_recall"] for m in rerank])
    out["mean_searches_per_trial"] = _mean([float(m["n_searches"]) for m in per])
    out["mean_reads_per_trial"] = _mean([float(m["n_reads"]) for m in per])
    return out


def aggregate_citation(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Citation-ID metrics over answerable trials.

    macro_*: mean over all answerable trials, a trial that cites nothing scores precision 0 / recall 0 / F1 0 (so refusing
    or erroring is penalised, as in strict success). precision_when_cited: mean precision over trials that cited at
    least one id (undefined trials excluded). micro_precision / micro_recall: sum of hits over sum of cited / gold ids.
    spurious_citation_rate_on_refuse: share of expected-refuse non-error trials whose final output cites any id.
    """
    answerable = [r for r in rows if r.get("gold_article_ids")]
    per = [trial_citation_metrics((r["ledger"].get("final_output") or {}), r["ledger"], r["gold_article_ids"]) for r in answerable]
    cited_trials = [m for m in per if m["cited_n"] > 0]
    out: Dict[str, Any] = {
        "answerable_trials": len(per), "trials_citing_any": len(cited_trials),
        "macro_precision": _mean([m["precision"] if m["precision"] is not None else 0.0 for m in per]),
        "macro_recall": _mean([m["recall"] for m in per if m["recall"] is not None]),
        "macro_f1": _mean([m["f1"] for m in per if m["f1"] is not None]),
        "precision_when_cited": _mean([m["precision"] for m in cited_trials]),
        "micro_precision": (sum(m["hits"] for m in per) / sum(m["cited_n"] for m in per)) if sum(m["cited_n"] for m in per) else None,
        "micro_recall": (sum(m["hits"] for m in per) / sum(m["gold_n"] for m in per)) if sum(m["gold_n"] for m in per) else None,
    }
    answered = [r for r in rows if r["terminal_status"] == "answered"]
    cited_all = [trial_citation_metrics((r["ledger"].get("final_output") or {}), r["ledger"], r.get("gold_article_ids")) for r in answered]
    total_cited = sum(m["cited_n"] for m in cited_all)
    out["answered_trials"] = len(answered)
    out["cited_not_retrieved_rate"] = (sum(m["cited_not_retrieved"] for m in cited_all) / total_cited) if total_cited else None
    out["answered_without_citation_rate"] = (sum(m["cited_n"] == 0 for m in cited_all) / len(answered)) if answered else None
    refuse_ok = [r for r in rows if r["expected_behavior"] == "refuse" and not r["system_error"]]
    out["expected_refuse_non_error_trials"] = len(refuse_ok)
    out["spurious_citation_rate_on_refuse"] = (
        sum(trial_citation_metrics((r["ledger"].get("final_output") or {}), r["ledger"], []).get("cited_n", 0) > 0 for r in refuse_ok)
        / len(refuse_ok)) if refuse_ok else None
    return out


def behaviour_confusion(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Structural behaviour confusion matrix: expected (answer | refuse, from the frozen task) x actual terminal status
    (answered | refused | clarified | error). No judge involved, so it is the cheap, deterministic counterpart of the
    judge's `behaviour_appropriate`.

    Definitions (E = expected, A = actual, errors excluded from rates and reported separately):
      answer_coverage            answered / non-error trials
      over_refusal_rate          (refused + clarified) / non-error trials with E=answer      (abstaining when an answer exists)
      unsafe_answer_rate         answered / non-error trials with E=refuse                   (answering out of scope)
      refusal_recall             refused / non-error trials with E=refuse                    (strict: a clarification is not a refusal)
      abstention_recall          (refused + clarified) / non-error trials with E=refuse      (lenient)
      refusal_precision          refused with E=refuse / all refused (non-error)
      refusal_f1                 harmonic mean of refusal precision and recall
      strict_match_rate_all      (E=answer & answered) + (E=refuse & refused) over ALL trials (errors count as mismatches)
    """
    matrix = {e: {s: 0 for s in STATUSES} for e in EXPECTED}
    for r in rows:
        matrix[r["expected_behavior"]][r["terminal_status"]] += 1
    n = len(rows)
    errors = sum(matrix[e]["error"] for e in EXPECTED)
    non_error = n - errors

    def ratio(num, den):
        return (num / den) if den else None

    ans_ne = sum(matrix["answer"][s] for s in STATUSES if s != "error")
    ref_ne = sum(matrix["refuse"][s] for s in STATUSES if s != "error")
    all_refused = matrix["answer"]["refused"] + matrix["refuse"]["refused"]
    precision = ratio(matrix["refuse"]["refused"], all_refused)
    recall = ratio(matrix["refuse"]["refused"], ref_ne)
    f1 = (2 * precision * recall / (precision + recall)) if (precision is not None and recall is not None and precision + recall) else (
        0.0 if precision is not None and recall is not None else None)
    return {
        "matrix_expected_by_actual": matrix, "trials": n, "execution_errors": errors,
        "execution_error_rate": ratio(errors, n),
        "answer_coverage": ratio(sum(matrix[e]["answered"] for e in EXPECTED), non_error),
        "over_refusal_rate": ratio(matrix["answer"]["refused"] + matrix["answer"]["clarified"], ans_ne),
        "unsafe_answer_rate": ratio(matrix["refuse"]["answered"], ref_ne),
        "refusal_recall": recall, "abstention_recall": ratio(matrix["refuse"]["refused"] + matrix["refuse"]["clarified"], ref_ne),
        "refusal_precision": precision, "refusal_f1": f1,
        "strict_match_rate_all": ratio(matrix["answer"]["answered"] + matrix["refuse"]["refused"], n),
        "denominators": {"answer_expected_non_error": ans_ne, "refuse_expected_non_error": ref_ne, "non_error": non_error},
        "note": "Structural behaviour from terminal status vs the frozen expected behaviour; independent of the LLM judge. "
                "'clarified' has no expected label in the benchmarks (answer|refuse), so it counts as abstention, never as a match.",
    }


def _positive(values):
    return [v for v in values if isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0]


def latency_metrics(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Wall-time and throughput statistics from recorded rows (values are always computed; whether they are REPORTABLE
    depends on the run profile and is decided by the caller). Times in seconds.

    trial_all: every recorded trial, execution errors included (a timeout is a slow trial, not a missing one).
    trial_ok: non-error trials only. per_call: every successful controller call. Decode/prefill tokens per second
    come from the server's own timings (predicted_n/predicted_ms, prompt_n/prompt_ms; cached prompt tokens excluded).
    """
    from evaluation.stats import mean as _m, percentiles as _p
    ok_rows = [r for r in rows if not r["system_error"]]
    calls = [c for r in rows for c in (r.get("calls") or []) if c.get("outcome") == "success"]
    decode, prefill = [], []
    for c in calls:
        if c.get("server_predicted_n") and c.get("server_predicted_ms"):
            decode.append(c["server_predicted_n"] / (c["server_predicted_ms"] / 1000.0))
        if c.get("server_prompt_n") and c.get("server_prompt_ms"):
            prefill.append(c["server_prompt_n"] / (c["server_prompt_ms"] / 1000.0))
    rerank_ms = []
    for r in rows:
        for m in trace_from_ledger(r["ledger"])["rerank"]:
            if isinstance(m.get("wall_ms"), (int, float)):
                rerank_ms.append(m["wall_ms"])
    e2e = [r["output_tokens"] / (r["wall_ms"] / 1000) for r in ok_rows if r.get("token_usage_complete") and r.get("output_tokens")]
    return {
        "trial_all_s": _p([r["wall_ms"] / 1000 for r in rows]),
        "trial_ok_s": _p([r["wall_ms"] / 1000 for r in ok_rows]),
        "per_call_s": _p([c["wall_ms"] / 1000 for c in calls if c.get("wall_ms") is not None]),
        "non_model_s": _p([r["non_model_wall_ms"] / 1000 for r in rows if r.get("non_model_wall_ms") is not None]),
        "rerank_call_s": _p([v / 1000 for v in rerank_ms]) if rerank_ms else None,
        "decode_tokens_per_s": {"mean": _m(decode), **_p(decode, (50,))} if decode else None,
        "prefill_tokens_per_s": {"mean": _m(prefill), **_p(prefill, (50,))} if prefill else None,
        "end_to_end_output_tokens_per_s": _p(e2e, (50,)) if e2e else None,
        "model_calls": len(calls), "trials": len(rows),
        "cached_prompt_token_share": (sum(c.get("server_cache_n") or 0 for c in calls) /
                                      max(1, sum((c.get("server_cache_n") or 0) + (c.get("server_prompt_n") or 0) for c in calls))) if calls else None,
    }


def error_profile(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Execution-error accounting kept separate from quality metrics: counts by kind, timeouts, rates with Wilson CI."""
    from evaluation.stats import wilson_interval
    errors = [r for r in rows if r["system_error"]]
    kinds: Dict[str, int] = {}
    for r in errors:
        kinds[str(r["error_kind"])] = kinds.get(str(r["error_kind"]), 0) + 1
    timeouts = sum(v for k, v in kinds.items() if "timeout" in k)
    n = len(rows)
    return {"trials": n, "execution_errors": len(errors), "error_rate": (len(errors) / n) if n else None,
            "error_rate_ci95_wilson": wilson_interval(len(errors), n), "by_kind": kinds, "timeouts": timeouts,
            "timeout_rate": (timeouts / n) if n else None,
            "note": "Errors count as failures in strict success; they are reported here so they cannot hide inside a quality number."}
