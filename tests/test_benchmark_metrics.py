"""Metric functions on REAL recorded run artifacts.

The fixture is evaluation/runs/bench-smoke-both-20261023: 18 real trials (2 benchmarks x 3 variants x 3 tasks, seed 42)
recorded from the native Bonsai controller, with the real DeepSeek-judge attempts. Nothing here is mocked or invented:
expected values are recomputed by hand from the recorded ledgers, or come from textbook examples for the pure statistics.
Human-label agreement is NOT tested on made-up labels (AGENTS.md); only its refusal to produce numbers is tested.
"""
import csv
import json
import shutil
from collections import Counter
from pathlib import Path

import numpy as np
import pytest

from evaluation import judge_benchmark as jb
from evaluation import metrics as m
from evaluation import run_benchmark as rb
from evaluation import run_d2
from evaluation import score_benchmark_audit as audit
from evaluation import stats

REPO = Path(__file__).resolve().parents[1]
RUN = REPO / "evaluation" / "runs" / "bench-smoke-both-20261023"


@pytest.fixture(scope="module")
def rows():
    found = rb.read_rows(rb.trials_path(RUN))
    assert len(found) == 18, "the recorded smoke run is the test fixture"
    return found


@pytest.fixture(scope="module")
def analysed(tmp_path_factory):
    work = tmp_path_factory.mktemp("analysed") / "run"
    shutil.copytree(RUN, work)
    jb.analyze(work, audit_size=3)
    return work, json.loads((work / "analysis" / "summary.json").read_text())


# ----------------------------------------------------------------------------- pure statistics (textbook values)

def test_cohen_kappa_textbook_example():
    # 50 items: both yes 20, A yes/B no 5, A no/B yes 10, both no 15 -> po 0.70, pe 0.50, kappa 0.40 (the standard worked example)
    a = [True] * 25 + [False] * 25
    b = [True] * 20 + [False] * 5 + [True] * 10 + [False] * 15
    result = stats.cohen_kappa(a, b)
    assert result["observed_agreement"] == pytest.approx(0.70)
    assert result["chance_agreement"] == pytest.approx(0.50)
    assert result["kappa"] == pytest.approx(0.40)
    assert stats.percent_agreement(a, b) == pytest.approx(0.70)


def test_kappa_is_undefined_not_zero_when_chance_agreement_is_total_or_there_are_no_items():
    assert stats.cohen_kappa([True, True, True], [True, True, True])["kappa"] is None   # both constant: pe = 1, kappa undefined
    assert stats.cohen_kappa([True, True, True], [True, False, True])["kappa"] == pytest.approx(0.0)  # one constant rater: defined, zero
    assert stats.cohen_kappa([], [])["kappa"] is None
    assert stats.percent_agreement([], []) is None


def test_linear_weighted_kappa_penalises_distant_disagreement_more():
    near = stats.cohen_kappa([0, 1, 2, 2, 1, 0], [0, 1, 1, 2, 1, 0], scheme="linear", order=[0, 1, 2])["kappa"]
    far = stats.cohen_kappa([0, 1, 2, 2, 1, 0], [0, 1, 0, 2, 1, 0], scheme="linear", order=[0, 1, 2])["kappa"]
    assert near > far


def test_wilson_interval_known_value():
    lo, hi = stats.wilson_interval(0, 10)
    assert lo == 0.0 and hi == pytest.approx(3.8416 / 13.8416, abs=1e-4)
    assert stats.wilson_interval(0, 0) is None


def test_percentiles_match_numpy_and_report_n():
    values = [1.0, 2.0, 4.0, 8.0, 16.0]
    result = stats.percentiles(values)
    assert result == {"p50": float(np.percentile(values, 50)), "p95": float(np.percentile(values, 95)), "n": 5}
    assert stats.percentiles([]) == {"p50": None, "p95": None, "n": 0}


# ----------------------------------------------------------------------------- bootstrap on real per-task values

def per_task_success(analysis_details, benchmark, variant):
    per = {}
    for d in analysis_details:
        if d["benchmark"] == benchmark and d["variant"] == variant:
            per.setdefault(d["task_id"], []).append(1.0 if d.get("success") is True else 0.0)
    return {t: float(np.mean(v)) for t, v in per.items()}


def test_paired_bootstrap_is_reproducible_antisymmetric_and_consistent(analysed):
    work, _ = analysed
    details = json.loads((work / "analysis" / "private-trial-details.json").read_text())
    a = per_task_success(details, "hcmut_v1", "off")
    b = per_task_success(details, "hcmut_v1", "l1")
    first = stats.paired_bootstrap(a, b)
    again = stats.paired_bootstrap(a, b)
    flipped = stats.paired_bootstrap(b, a)
    assert first == again  # fixed bootstrap seed
    assert first["diff_b_minus_a"] == pytest.approx(np.mean([b[t] - a[t] for t in a]))
    assert flipped["diff_b_minus_a"] == pytest.approx(-first["diff_b_minus_a"])
    assert first["ci95"][0] <= first["diff_b_minus_a"] <= first["ci95"][1]
    assert first["units_b_better"] + first["units_a_better"] + first["units_tied"] == first["n_units"] == len(a)
    assert stats.paired_bootstrap({"x": 1.0}, {"x": 0.0}) is None  # one unit: no interval is invented


def test_bootstrap_mean_ci_contains_the_mean_and_needs_two_units():
    values = [0.0, 1.0, 1.0, 0.0, 1.0, 1.0]
    result = stats.bootstrap_mean_ci(values)
    assert result["mean"] == pytest.approx(4 / 6) and result["ci95"][0] <= result["mean"] <= result["ci95"][1]
    assert stats.bootstrap_mean_ci([1.0]) is None


# ----------------------------------------------------------------------------- retrieval / citation / behaviour from real ledgers

def test_retrieval_metrics_equal_a_hand_computation_from_the_recorded_ledger(rows):
    checked = 0
    for row in rows:
        if not row["gold_article_ids"]:
            continue
        ledger = row["ledger"]
        gold = {m.normalize_id(g) for g in row["gold_article_ids"]}
        surfaced = list(dict.fromkeys(m.normalize_id(i) for i in ledger["retrieved_article_ids"]))
        metrics = m.trial_retrieval_metrics(ledger, row["gold_article_ids"])
        for k in (1, 3, 5):
            assert metrics[f"Recall@{k}"] == pytest.approx(len(gold & set(surfaced[:k])) / len(gold))
        ranks = [i + 1 for i, doc in enumerate(surfaced) if doc in gold]
        assert metrics["MRR"] == pytest.approx(round(1 / min(ranks), 4) if ranks else 0.0)
        assert metrics["trace_recall"] == pytest.approx(len(gold & set(surfaced)) / len(gold))
        # the value the runner stored at collection time agrees with the analysis recomputation
        for key in ("Recall@1", "Recall@3", "Recall@5", "MRR"):
            assert metrics[key] == pytest.approx(row["retrieval"][key])
        checked += 1
    assert checked >= 10


def test_ndcg_is_one_for_a_perfect_ranking_and_zero_without_gold():
    assert m.ndcg_at_k(["a", "b", "c"], ["a", "b"], 5) == pytest.approx(1.0)
    assert m.ndcg_at_k(["c", "a"], ["a"], 5) == pytest.approx(1 / np.log2(3))
    assert m.ndcg_at_k(["a"], [], 5) == 0.0


def test_citation_precision_is_undefined_when_nothing_is_cited_and_f1_follows(rows):
    seen_none = seen_some = 0
    for row in rows:
        if not row["gold_article_ids"]:
            continue
        final = row["ledger"]["final_output"]
        cited = {m.normalize_id(c["article_id"]) for c in final.get("citations", []) if isinstance(c, dict)}
        result = m.trial_citation_metrics(final, row["ledger"], row["gold_article_ids"])
        gold = {m.normalize_id(g) for g in row["gold_article_ids"]}
        if not cited:
            assert result["precision"] is None and result["f1"] == 0.0 and result["recall"] == 0.0
            seen_none += 1
        else:
            p, r = len(cited & gold) / len(cited), len(cited & gold) / len(gold)
            assert result["precision"] == pytest.approx(p) and result["recall"] == pytest.approx(r)
            assert result["f1"] == pytest.approx(0.0 if p + r == 0 else 2 * p * r / (p + r))
            assert result["precision"] == pytest.approx(row["citation"]["citation_precision"], abs=1e-4)  # legacy (rounded to 4 digits) value agrees when something is cited
            seen_some += 1
    assert seen_none and seen_some


def test_behaviour_confusion_counts_equal_the_recorded_statuses(rows):
    result = m.behaviour_confusion(rows)
    counts = Counter((r["expected_behavior"], r["terminal_status"]) for r in rows)
    for expected in ("answer", "refuse"):
        for status in ("answered", "refused", "clarified", "error"):
            assert result["matrix_expected_by_actual"][expected][status] == counts[(expected, status)]
    assert sum(sum(v.values()) for v in result["matrix_expected_by_actual"].values()) == len(rows) == result["trials"]
    answerable_non_error = sum(v for (e, s), v in counts.items() if e == "answer" and s != "error")
    assert result["over_refusal_rate"] == pytest.approx(
        (counts[("answer", "refused")] + counts[("answer", "clarified")]) / answerable_non_error)
    refused = counts[("answer", "refused")] + counts[("refuse", "refused")]
    assert result["refusal_precision"] == pytest.approx(counts[("refuse", "refused")] / refused)
    assert result["strict_match_rate_all"] == pytest.approx((counts[("answer", "answered")] + counts[("refuse", "refused")]) / len(rows))


def test_latency_metrics_equal_numpy_on_recorded_wall_times(rows):
    lat = m.latency_metrics(rows)
    wall = [r["wall_ms"] / 1000 for r in rows]
    assert lat["trial_all_s"]["p50"] == pytest.approx(np.percentile(wall, 50))
    assert lat["trial_all_s"]["p95"] == pytest.approx(np.percentile(wall, 95))
    calls = [c["wall_ms"] / 1000 for r in rows for c in r["calls"] if c["outcome"] == "success"]
    assert lat["per_call_s"]["n"] == len(calls) and lat["per_call_s"]["p50"] == pytest.approx(np.percentile(calls, 50))
    assert 20 < lat["decode_tokens_per_s"]["p50"] < 400  # tokens/s from the server's own timings, plausible for a 2B model
    assert lat["rerank_call_s"]["n"] == 6  # six recorded rerank searches in the fixture


def test_error_profile_keeps_errors_separate_and_reports_zero_when_none(rows):
    profile = m.error_profile(rows)
    assert profile["execution_errors"] == 0 and profile["error_rate"] == 0.0 and profile["by_kind"] == {}
    assert profile["error_rate_ci95_wilson"][0] == 0.0 and profile["error_rate_ci95_wilson"][1] > 0.0


# ----------------------------------------------------------------------------- analysis on the real run

def test_analysis_numbers_equal_an_independent_recomputation(analysed):
    work, summary = analysed
    check = run_d2.recompute_headlines(work)
    assert check["all_match"], check
    assert summary["analysis_version"] == 3 and summary["report_eligible"] is False  # a smoke run is never report evidence
    assert set(summary["cells"]) == {f"{b}/{v}" for b in ("hcmut_v1", "labour_vi_v1") for v in ("off", "l1", "l1_rerank")}
    for cell in summary["cells"].values():
        assert cell["errors"]["execution_errors"] == cell["counts"]["execution_errors"] == 0
        assert cell["strict_success"]["rate_lower_bound"] <= cell["strict_success"]["rate_upper_bound"]
        assert cell["citation_id"]["f1"] is not None and cell["behaviour_confusion"]["trials"] == 3
        assert cell["latency"]["reportable"] is True and cell["latency"]["trial_p50_s"] <= cell["latency"]["trial_p95_s"]
        assert cell["latency"]["decode_tokens_per_s_p50"] > 0 and cell["tokens"]["native_calls_per_trial"] >= 2


def test_retrieval_saturation_is_measured_and_strata_are_reported(analysed):
    _, summary = analysed
    for cell in summary["cells"].values():
        r = cell["retrieval"]
        assert 0.0 <= r["share_full_recall_at_5"] <= 1.0 and "saturated" in r["ceiling_note"]
        assert sum(r["gold_ids_per_trial_distribution"].values()) == r["answerable_trials"]
        groups = cell["by_stratum_group"]
        assert set(groups) <= {"guessable", "not_guessable", "refusal_task"} and sum(g["trials"] for g in groups.values()) == cell["trials_recorded"]
        assert "LLM estimates" in cell["stratum_note"]
    paired = next(iter(summary["paired_differences"]["comparisons"].values()))
    assert set(paired["pooled_strict_success_by_stratum_group"]) <= {"guessable", "not_guessable", "refusal_task"}


def test_paired_differences_cover_the_configured_comparisons_and_the_pool(analysed):
    _, summary = analysed
    paired = summary["paired_differences"]["comparisons"]
    assert set(paired) == {"L1 vs OFF", "L1+rerank vs L1", "L1+rerank vs OFF"}
    for entry in paired.values():
        assert set(entry["by_benchmark"]) == {"hcmut_v1", "labour_vi_v1"}
        pooled = entry["pooled"]["strict_success_lower"]
        assert pooled["n_units"] == 6 and pooled["ci95"][0] <= pooled["diff_b_minus_a"] <= pooled["ci95"][1]


def test_judge_cost_and_invalid_judgments_are_accounted_not_hidden(analysed):
    _, summary = analysed
    cost = summary["judge_cost_total"]
    assert cost["attempts"] == 26 and cost["valid_attempts"] == 18
    assert cost["invalid_attempt_share"] == pytest.approx(8 / 26)
    assert sum(cost["invalid_reasons"].values()) == 8
    assert 0.001 < cost["usd_per_valid_packet"] < 0.01  # the figure behind the planning estimate in d2_matrix.yaml


def test_no_metric_input_comes_from_gold_into_the_agent_call():
    """The agent is called with the question (and pasted document) only; gold ids are used after the trial.

    WHITELIST (explicit, by design): the diagnostic ORACLE baseline is given the gold records. That is the one `agent.prepare_trial(task)`
    call in execute_trial, guarded by `getattr(agent, "uses_gold", False)`; `uses_gold` must be True for OracleBaselineAgent and for no other class.
    """
    import ast
    tree = ast.parse((REPO / "evaluation" / "run_benchmark.py").read_text(encoding="utf-8"))   # the file on disk, not inspect/linecache
    execute = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "execute_trial")
    target = next(n for n in ast.walk(execute) if isinstance(n, ast.FunctionDef) and n.name == "target")
    calls = [n for n in ast.walk(target) if isinstance(n, ast.Call) and getattr(n.func, "attr", "") == "run"]
    assert len(calls) == 1
    names = {a.arg for a in calls[0].keywords}
    text = ast.unparse(calls[0])
    assert names == {"pasted_doc", "session_id"} and "ground_truth" not in text and "gold" not in text and "expected" not in text
    # the whitelisted oracle entry: exactly one prepare_trial call, under the uses_gold guard
    guarded = [n for n in ast.walk(target) if isinstance(n, ast.If) and "uses_gold" in ast.unparse(n.test)]
    assert len(guarded) == 1 and [ast.unparse(c) for c in ast.walk(guarded[0]) if isinstance(c, ast.Call) and getattr(c.func, "attr", "") == "prepare_trial"] == ["agent.prepare_trial(task)"]
    assert sum(isinstance(n, ast.Call) and getattr(n.func, "attr", "") == "prepare_trial" for n in ast.walk(target)) == 1
    base = ast.parse((REPO / "evaluation" / "baselines.py").read_text(encoding="utf-8"))
    flags = {c.name: [ast.unparse(a.value) for a in c.body if isinstance(a, ast.Assign) and any(getattr(t, "id", "") == "uses_gold" for t in a.targets)]
             for c in base.body if isinstance(c, ast.ClassDef)}
    assert {k: v for k, v in flags.items() if v} == {"BaselineAgent": ["False"], "OracleBaselineAgent": ["True"]}
    from src.agent.loop import LuatCheckAgent
    assert not getattr(LuatCheckAgent, "uses_gold", False)   # no system variant is ever given gold


# ----------------------------------------------------------------------------- strict-success rule for refusals (recorded judgments)

SMOKE = REPO / "evaluation" / "runs" / "bench-smoke-evalimpl-20261023"


def test_correct_refusals_are_not_failed_by_their_own_absence_statement():
    """Recorded judgments of a real run: the judge listed the refusal sentence as a not_established claim on 3 of 12 trials."""
    from evaluation import judge_rules
    packets = {p["review_id"]: p for p in json.loads((SMOKE / "judge" / "judge_packets.json").read_text())}
    judgments = {}
    for line in (SMOKE / "judge" / "judgments.jsonl").read_text().splitlines():
        row = json.loads(line)
        if row["status"] == "valid" and row["judgment"]["judgeable"]:
            judgments[row["review_id"]] = row["judgment"]
    flipped = unchanged = 0
    for rid, j in judgments.items():
        packet = packets[rid]
        abstention = judge_rules.is_abstention(packet["expected_behavior"], packet["candidate_behavior"])
        old = bool(j["behaviour_appropriate"] and j["correctness"] == 2 and j["completeness"] == 2 and all(c["support"] == "supported" for c in j["claims"]))
        new = judge_rules.judgment_strict_success(j, abstention)
        if new != old:
            flipped += 1
            assert abstention and new and not old
            assert j["behaviour_appropriate"] and j["correctness"] == 2 and j["completeness"] == 2
            assert j["claims"] and all(c["support"] == "not_established" for c in j["claims"])   # only the absence statement(s)
            assert not any(c["support"] == "contradicted" for c in j["claims"])
        else:
            unchanged += 1
        if not abstention:
            assert new == old   # answer outputs keep the all-claims-supported rule
        if any(c["support"] == "contradicted" for c in j["claims"]):
            assert new is False   # a contradicted claim always fails
    assert flipped == 3 and flipped + unchanged == len(judgments) == 11   # 12 judged packets, 1 of them judge-unjudgeable (unknown)


def test_analysis_counts_the_three_correct_refusals_as_successes(tmp_path):
    work = tmp_path / "run"
    shutil.copytree(SMOKE, work)
    summary = jb.analyze(work, audit_size=3)
    assert sum(c["strict_success"]["successes"] for c in summary["cells"].values()) == 3   # was 0 of 12 under the all-claims-supported rule
    assert sum(c["claim_faithfulness"]["ignored_absence_claims_in_abstention_outputs"] for c in summary["cells"].values()) >= 3
    assert run_d2.recompute_headlines(work)["all_match"]
    assert (work / "judge" / "SEMANTIC_JUDGING.md").read_text() == (SMOKE / "judge" / "SEMANTIC_JUDGING.md").read_text()   # protocol of a judged run is never rewritten


def test_contradicted_claims_and_wrong_scores_still_fail_an_abstention():
    from evaluation import judge_rules
    base = {"behaviour_appropriate": True, "correctness": 2, "completeness": 2,
            "claims": [{"support": "not_established"}]}
    assert judge_rules.judgment_strict_success(base, True) is True
    assert judge_rules.judgment_strict_success({**base, "claims": [{"support": "not_established"}, {"support": "contradicted"}]}, True) is False
    assert judge_rules.judgment_strict_success({**base, "correctness": 1}, True) is False
    assert judge_rules.judgment_strict_success({**base, "behaviour_appropriate": False}, True) is False
    assert judge_rules.judgment_strict_success(base, False) is False   # an answer must have every claim supported
    assert judge_rules.is_abstention("refuse", "answered") and judge_rules.is_abstention("answer", "clarified") and not judge_rules.is_abstention("answer", "answered")


# ----------------------------------------------------------------------------- audit scorer: refusal to invent numbers

def test_audit_scorer_withholds_numbers_for_blank_labels(tmp_path):
    work = tmp_path / "run"
    shutil.copytree(RUN, work)
    jb.analyze(work, audit_size=3)  # writes the blank human-audit export
    result = audit.score(work, [work / "analysis" / "human-audit" / "labels.csv"])
    assert result["status"] == "no_labels" and result["judge_vs_human"] is None and result["per_reviewer"] is None
    assert result["sample_size"] == len(json.loads((work / "analysis" / "human-audit" / "packets.json").read_text())) > 0
    assert audit.main(["--run-dir", str(work)]) == audit.EXIT["no_labels"]
    assert json.loads((work / "analysis" / "human-audit" / "agreement.json").read_text())["judge_vs_human"] is None


def test_audit_scorer_rejects_malformed_rows_without_producing_numbers(tmp_path):
    work = tmp_path / "run"
    shutil.copytree(RUN, work)
    jb.analyze(work, audit_size=3)
    sample = json.loads((work / "analysis" / "human-audit" / "packets.json").read_text())
    rid = sample[0]["review_id"]
    bad = tmp_path / "bad.csv"
    with bad.open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(audit.LABEL_COLUMNS)
        writer.writerow([rid, "", "1", "1", "2", "2", "3", "0", ""])                      # labels but no reviewer
        writer.writerow(["not-in-the-sample", "someone", "1", "1", "2", "2", "3", "0", ""])  # item outside the sample
        writer.writerow([rid, "someone", "1", "1", "5", "2", "3", "0", ""])                # correctness out of range
        writer.writerow([rid, "someone", "1", "1", "2", "2", "3", "7", ""])                # more unsupported than total claims
        writer.writerow([rid, "someone", "", "1", "", "", "", "", ""])                     # half-filled row
    result = audit.score(work, [bad])
    assert result["status"] == "invalid_labels" and result["judge_vs_human"] is None
    assert len(result["problems"]) == 5
    assert audit.main(["--run-dir", str(work), "--labels", str(bad)]) == audit.EXIT["invalid_labels"]


def test_audit_scorer_requires_real_columns(tmp_path):
    work = tmp_path / "run"
    shutil.copytree(RUN, work)
    jb.analyze(work, audit_size=3)
    wrong = tmp_path / "wrong.csv"
    wrong.write_text("review_id,reviewer\nx,y\n")
    assert audit.score(work, [wrong])["status"] == "invalid_labels"


# ----------------------------------------------------------------------------- diagnostic baselines on a recorded run

BASELINE_RUN = REPO / "evaluation" / "runs" / "bench-smoke-baselines-rerank-20261024"   # off, l1_rerank + closed_book, oracle; 2 tasks per benchmark, seed 42


def test_baselines_are_separate_cells_never_pooled_and_reported_in_their_own_table(tmp_path):
    from evaluation import render_benchmark_tables as render
    work = tmp_path / "run"
    shutil.copytree(BASELINE_RUN, work)
    summary = jb.analyze(work, audit_size=3)
    assert set(summary["baselines"]) == {"closed_book", "oracle"}
    arms = {k: c["arm"] for k, c in summary["cells"].items()}
    assert arms["hcmut_v1/oracle"] == arms["labour_vi_v1/closed_book"] == "baseline" and arms["hcmut_v1/off"] == "system"
    for key, cell in summary["cells"].items():
        if cell["arm"] == "baseline":
            assert cell["retrieval"]["Recall@5"] is None and cell["retrieval"]["MRR"] is None   # retrieval is not defined for a no-search baseline
            assert cell["answerable_by_gold_surfaced"] is None and cell["seeds"] == [42]
    # no baseline in any paired system comparison
    for entry in summary["paired_differences"]["comparisons"].values():
        assert {entry["baseline"], entry["treatment"]} <= {"off", "l1", "l1_rerank"}
    # the oracle only ran answerable tasks; its citations are checked against gold; closed-book ran refuse tasks too
    oracle = [json.loads(l) for l in (work / "trials.jsonl").read_text().splitlines() if '"variant": "oracle"' in l]
    assert oracle and all(r["expected_behavior"] == "answer" and r["gold_article_ids"] for r in oracle)
    for r in oracle:
        assert r["ledger"]["retrieved_article_ids"] == r["gold_article_ids"] and not [e for e in r["ledger"]["audit_events"] if e.get("event") == "tool_call"]
        assert r["kind"] == "oracle" and r["verification_mode"] == "off"
    assert summary["cells"]["hcmut_v1/oracle"]["citation_id"]["precision"] is not None
    tex = render.render(summary, ["hcmut_v1", "labour_vi_v1"], ["off", "l1_rerank"])["results"]
    assert "tab:benchmark-baselines" in tex and "Diagnostic baselines" in tex and "never pooled" in tex
    main_table = tex.split("tab:benchmark-main")[0]
    assert "oracle" not in main_table and "closed" not in main_table   # system tables carry no baseline row
    assert run_d2.recompute_headlines(work)["all_match"]
    assert sum(c["trials_recorded"] for c in summary["cells"].values() if c["arm"] == "system") == 8   # baselines do not inflate the system trial count
