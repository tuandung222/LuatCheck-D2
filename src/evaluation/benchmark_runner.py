"""
Data Scientist Friendly Benchmark Runner for LuatCheck.

Provides an object-oriented Python API for executing quantitative evaluations
in Jupyter Notebooks or batch scripts. Supports exporting evaluation metrics
and error taxonomy breakdown directly to Pandas DataFrames.
"""
import json
import time
import random
import os
from typing import List, Dict, Any, Optional
import numpy as np
import pandas as pd

from src.agent.loop import LuatCheckAgent
from src.agent.state import Citation
from evaluation.metrics import (
    calculate_retrieval_metrics,
    calculate_citation_metrics,
    calculate_latency_percentiles,
    calculate_unsupported_rate,
    normalize_id
)
from evaluation.error_analyzer import ErrorDiagnosticAnalyzer


class BenchmarkRunner:
    """Quantitative evaluation runner designed for data scientists and experimenters."""

    def __init__(
        self,
        agent: Optional[LuatCheckAgent] = None,
        tasks_path: str = "evaluation/tasks/vlqa_full_20.json",
        cold_cache_isolation: bool = True
    ):
        self.agent = agent or LuatCheckAgent.default()
        self.tasks_path = tasks_path
        self.cold_cache_isolation = cold_cache_isolation
        self.tasks = self._load_tasks(tasks_path)
        self.latest_results: Dict[str, Any] = {}
        self.latest_analyzer: Optional[ErrorDiagnosticAnalyzer] = None

    def _load_tasks(self, path: str) -> List[Dict[str, Any]]:
        if not os.path.exists(path):
            raise FileNotFoundError(f"Evaluation dataset file not found at: {path}")
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def run(
        self,
        seeds: List[int] = [42, 123, 2026],
        mode: Optional[str] = None,
        verbose: bool = True
    ) -> Dict[str, Any]:
        """Execute multi-seed evaluation and aggregate metrics."""
        target_mode = mode or self.agent.verification_mode
        self.agent.verification_mode = target_mode
        self.agent.enable_verification = (target_mode != "off")

        if self.cold_cache_isolation:
            self.agent.sqlite_store.retrieve_similar_case = lambda *args, **kwargs: None
            self.agent.sqlite_store.write_if_verified = lambda *args, **kwargs: False

        error_analyzer = ErrorDiagnosticAnalyzer(name=target_mode)
        all_seed_results = []
        latencies = []
        total_token_counts = []

        for seed in seeds:
            random.seed(seed)
            np.random.seed(seed)
            if verbose:
                print(f"[BenchmarkRunner] Evaluating Seed {seed} across {len(self.tasks)} tasks...", flush=True)

            seed_recalls_1 = []
            seed_recalls_5 = []
            seed_mrrs = []
            seed_citation_precisions = []
            seed_citation_recalls = []
            seed_coverage = []
            seed_unsupported_rates = []

            for idx, task in enumerate(self.tasks):
                t_start = time.time()
                query = task["question"]
                gt_ids = task.get("ground_truth_article_ids", [])
                if not gt_ids and task.get("ground_truth_article_id"):
                    gt_ids = [task.get("ground_truth_article_id")]
                expected_behavior = task.get("expected_behavior", "answer")

                ledger = self.agent.run(query, session_id=f"bench_{target_mode}_s{seed}_t{idx}")
                t_elapsed = (time.time() - t_start) * 1000
                latencies.append(t_elapsed)

                final_out = ledger.final_output or {}
                citations = final_out.get("citations", [])
                cit_ids = []
                if citations:
                    for c in citations:
                        aid = c.get("article_id", "") if isinstance(c, dict) else getattr(c, "article_id", str(c))
                        if aid:
                            cit_ids.append(normalize_id(aid))

                if gt_ids:
                    ret_evaluated = ledger.retrieved_article_ids
                    ret_metrics = calculate_retrieval_metrics(ret_evaluated, gt_ids)
                    seed_recalls_1.append(ret_metrics["Recall@1"])
                    seed_recalls_5.append(ret_metrics["Recall@5"])
                    seed_mrrs.append(ret_metrics["MRR"])

                is_answered = (ledger.terminal_status == "answered")
                seed_coverage.append(1.0 if is_answered else 0.0)

                if gt_ids:
                    cit_metrics = calculate_citation_metrics(cit_ids, gt_ids)
                    seed_citation_precisions.append(cit_metrics["citation_precision"])
                    seed_citation_recalls.append(cit_metrics["citation_recall"])
                else:
                    cit_metrics = calculate_citation_metrics(cit_ids, [])
                    seed_citation_precisions.append(cit_metrics["citation_precision"])
                    seed_citation_recalls.append(cit_metrics["citation_recall"])

                unsupported_claims_list = []
                if not is_answered:
                    usr = 0.0
                elif expected_behavior == "refuse":
                    usr = 1.0
                    unsupported_claims_list = [str(final_out.get("content", ""))]
                else:
                    answer_text = final_out.get("content", "")
                    if target_mode in ["l1_l2", "l1_l2_on"]:
                        usr = calculate_unsupported_rate(
                            answer_text=answer_text,
                            cited_articles=citations,
                            verifier=self.agent.verifier,
                            retrieved_article_ids=ledger.retrieved_article_ids
                        )
                        l2_res = self.agent.l2_verifier.verify_all_claims(answer_text, cit_ids)
                        unsupported_claims_list = [f["sentence"] for f in l2_res.get("failed_claims", [])]
                        if not l2_res.get("is_entailed", False) and usr == 0.0 and len(unsupported_claims_list) > 0:
                            total_sents = max(l2_res.get("total_sentences", 1), 1)
                            usr = round(float(len(unsupported_claims_list) / total_sents), 4)
                    else:
                        usr = calculate_unsupported_rate(
                            answer_text=answer_text,
                            cited_articles=citations,
                            verifier=self.agent.verifier,
                            retrieved_article_ids=ledger.retrieved_article_ids
                        )
                        cit_objs = [
                            Citation(article_id=c.get("article_id", ""), span=c.get("span", ""))
                            if isinstance(c, dict) else c
                            for c in citations
                        ]
                        l1_res = self.agent.verifier.verify(
                            answer_text=answer_text,
                            citations=cit_objs,
                            retrieved_article_ids=ledger.retrieved_article_ids
                        )
                        if hasattr(l1_res, "unsupported_claims"):
                            unsupported_claims_list = list(l1_res.unsupported_claims)

                seed_unsupported_rates.append(usr)
                prompt_tokens = int(len(query.split()) * 1.3) + 120
                out_tokens = int(len(str(final_out.get("content", "")).split()) * 1.3) if is_answered else 35
                total_token_counts.append(prompt_tokens + out_tokens)

                parse_error_detected = any(ev.get("event") == "parse_error" for ev in getattr(ledger, "audit_events", []))
                parse_error_details = None
                if parse_error_detected:
                    for ev in getattr(ledger, "audit_events", []):
                        if ev.get("event") == "parse_error":
                            parse_error_details = ev.get("details")
                            break

                error_analyzer.record_task_evaluation(
                    task=task,
                    ledger=ledger,
                    citations=citations,
                    unsupported_sentence_rate=usr,
                    unsupported_claims=unsupported_claims_list,
                    parse_error_detected=parse_error_detected,
                    parse_error_details=parse_error_details
                )

            all_seed_results.append({
                "seed": seed,
                "Recall@1": np.mean(seed_recalls_1) if seed_recalls_1 else 0.0,
                "Recall@5": np.mean(seed_recalls_5) if seed_recalls_5 else 0.0,
                "MRR": np.mean(seed_mrrs) if seed_mrrs else 0.0,
                "Citation_Precision": np.mean(seed_citation_precisions),
                "Citation_Recall": np.mean(seed_citation_recalls),
                "Coverage": np.mean(seed_coverage),
                "Unsupported_Rate": np.mean(seed_unsupported_rates)
            })

        error_stats = error_analyzer.get_statistics()
        aggregated = {
            "mode": target_mode,
            "seeds": seeds,
            "Recall@1_mean": round(float(np.mean([r["Recall@1"] for r in all_seed_results])), 4),
            "Recall@1_std": round(float(np.std([r["Recall@1"] for r in all_seed_results])), 4),
            "Recall@5_mean": round(float(np.mean([r["Recall@5"] for r in all_seed_results])), 4),
            "Recall@5_std": round(float(np.std([r["Recall@5"] for r in all_seed_results])), 4),
            "MRR_mean": round(float(np.mean([r["MRR"] for r in all_seed_results])), 4),
            "MRR_std": round(float(np.std([r["MRR"] for r in all_seed_results])), 4),
            "Citation_Precision_mean": round(float(np.mean([r["Citation_Precision"] for r in all_seed_results])), 4),
            "Citation_Precision_std": round(float(np.std([r["Citation_Precision"] for r in all_seed_results])), 4),
            "Citation_Recall_mean": round(float(np.mean([r["Citation_Recall"] for r in all_seed_results])), 4),
            "Citation_Recall_std": round(float(np.std([r["Citation_Recall"] for r in all_seed_results])), 4),
            "Coverage_mean": round(float(np.mean([r["Coverage"] for r in all_seed_results])), 4),
            "Coverage_std": round(float(np.std([r["Coverage"] for r in all_seed_results])), 4),
            "Unsupported_Rate_mean": round(float(np.mean([r["Unsupported_Rate"] for r in all_seed_results])), 4),
            "Unsupported_Rate_std": round(float(np.std([r["Unsupported_Rate"] for r in all_seed_results])), 4),
            "Error_Taxonomy": error_stats["counts"],
            "Latency": calculate_latency_percentiles(latencies),
            "Tokens_Per_Task_mean": round(float(np.mean(total_token_counts)), 1) if total_token_counts else 0.0,
            "Compute_Cost_USD": 0.0
        }
        self.latest_results = aggregated
        self.latest_analyzer = error_analyzer
        return aggregated

    def get_metrics_dataframe(self) -> pd.DataFrame:
        """Convert aggregated evaluation metrics into a Pandas DataFrame for plotting and analysis."""
        if not self.latest_results:
            raise ValueError("No evaluation results found. Please call runner.run() first.")
        res = self.latest_results
        data = [
            {"Metric": "Recall@1", "Mean": res["Recall@1_mean"], "Std": res["Recall@1_std"]},
            {"Metric": "Recall@5", "Mean": res["Recall@5_mean"], "Std": res["Recall@5_std"]},
            {"Metric": "MRR", "Mean": res["MRR_mean"], "Std": res["MRR_std"]},
            {"Metric": "Citation Precision", "Mean": res["Citation_Precision_mean"], "Std": res["Citation_Precision_std"]},
            {"Metric": "Citation Recall", "Mean": res["Citation_Recall_mean"], "Std": res["Citation_Recall_std"]},
            {"Metric": "Answer Coverage", "Mean": res["Coverage_mean"], "Std": res["Coverage_std"]},
            {"Metric": "Unsupported Rate (↓)", "Mean": res["Unsupported_Rate_mean"], "Std": res["Unsupported_Rate_std"]},
        ]
        return pd.DataFrame(data)

    def get_error_taxonomy_dataframe(self) -> pd.DataFrame:
        """Convert error taxonomy distribution into a Pandas DataFrame."""
        if not self.latest_results:
            raise ValueError("No evaluation results found. Please call runner.run() first.")
        taxonomy = self.latest_results.get("Error_Taxonomy", {})
        data = [{"Failure Mode": k, "Count": v} for k, v in taxonomy.items()]
        return pd.DataFrame(data)
