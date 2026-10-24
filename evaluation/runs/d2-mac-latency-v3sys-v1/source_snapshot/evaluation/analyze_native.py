"""Recompute directly measurable metrics from complete real native runs.

This module does not assign semantic/legal correctness. Lexical reference
agreement and the agent's own lexical checks are explicitly diagnostic.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import unicodedata
import numpy as np
from evaluation.score_reviewed_runs import read_runs
from evaluation.run_eval import sha256

def reference_overlap(prediction, reference):
    def tokens(value):
        return re.findall(r"\w+", unicodedata.normalize("NFC",value).casefold())
    predicted, expected = tokens(prediction), tokens(reference)
    overlap = sum((Counter(predicted)&Counter(expected)).values())
    precision = overlap/len(predicted) if predicted else 0.0
    recall = overlap/len(expected) if expected else 0.0
    return {"normalized_exact_match": float(predicted == expected),
            "token_f1": 2*precision*recall/(precision+recall) if precision+recall else 0.0}

def analyze(run_dir, tasks_file):
    manifest, rows = read_runs(run_dir)
    tasks = {t["task_id"]:t for t in json.loads(Path(tasks_file).read_text())}
    assert set(tasks) == set(manifest["task_ids"])
    recorded_task_hashes = {value for key,value in manifest["sources"]["files_sha256"].items()
                            if Path(key).name == Path(tasks_file).name}
    if sha256(tasks_file) not in recorded_task_hashes:
        raise ValueError("Analysis dataset hash is absent from frozen collection sources")
    result = {"run_dir":str(run_dir),"phase":manifest["phase"],"trials":len(rows),
              "collection_manifest_sha256":sha256(Path(run_dir)/"manifest.json"),
              "runs_sha256":sha256(Path(run_dir)/"runs.jsonl"),"tasks_sha256":sha256(tasks_file),
              "semantic_task_success":None,"semantic_unsupported_claim_rate":None,
              "human_judge_agreement":None,"hardware_GPU_active_hours":None,
              "note":"Measured operations and citation-ID/lexical diagnostics. No semantic or expert correctness score is inferred.",
              "modes":{}}
    details=[]
    for row in rows:
        final = row["ledger"].get("final_output") or {}
        task = tasks[row["task_id"]]
        actual = {"answered":"answer","refused":"refuse","clarified":"clarify"}.get(row["terminal_status"],"error")
        overlap = reference_overlap(final.get("content",""),task["expected_answer"]) if task["expected_behavior"]=="answer" else None
        details.append({"task_id":row["task_id"],"seed":row["seed"],"mode":row["mode"],
                        "terminal_status":row["terminal_status"],"terminal_behavior_agrees":actual==task["expected_behavior"],
                        "reference_overlap":overlap,"gold_articles":row["gold_article_ids"],
                        "retrieved_ids":row["ledger"]["retrieved_article_ids"],
                        "citation_ids":[c["article_id"] for c in final.get("citations",[])],
                        "wall_seconds":row["wall_ms"]/1000,"input_tokens":row["input_tokens"],
                        "output_tokens":row["output_tokens"],"tool_calls":row["ledger"]["tool_calls_count"],
                        "repairs":row["ledger"]["repairs_count"],"final_output":final})
    for mode in manifest["modes"]:
        sub=[r for r in rows if r["mode"]==mode]
        source_sub=[r for r in sub if r["gold_article_ids"]]
        detail=[r for r in details if r["mode"]==mode]
        answered=[r for r in sub if r["terminal_status"]=="answered"]
        reference=[d["reference_overlap"] for d in detail if d["reference_overlap"] is not None]
        input_complete=all(r["input_tokens"] is not None for r in sub)
        output_complete=all(r["output_tokens"] is not None for r in sub)
        calls=[c for r in sub for c in r["ledger"]["llm_calls"]]
        native_time=[c.get("total_duration_ns") for c in calls]
        input_tokens=sum(r["input_tokens"] for r in sub) if input_complete else None
        output_tokens=sum(r["output_tokens"] for r in sub) if output_complete else None
        by_seed=[]
        for seed in manifest["seeds"]:
            seed_rows=[r for r in source_sub if r["seed"]==seed]
            by_seed.append({"seed":seed,"trajectory_recall5":float(np.mean([r["retrieval"]["Recall@5"] for r in seed_rows])),
                            "citation_precision":float(np.mean([r["citation"]["citation_precision"] for r in seed_rows])),
                            "citation_recall":float(np.mean([r["citation"]["citation_recall"] for r in seed_rows]))})
        result["modes"][mode]={
            "trials":len(sub),"answered":len(answered),
            "refused":sum(r["terminal_status"]=="refused" for r in sub),
            "clarified":sum(r["terminal_status"]=="clarified" for r in sub),
            "execution_errors":sum(r["system_error"] for r in sub),
            "error_types":dict(Counter(r["error_kind"] for r in sub if r["system_error"])),
            "answer_coverage":len(answered)/len(sub),
            "answerable_trials":len(source_sub),
            "answerable_answer_coverage":sum(r["terminal_status"]=="answered" for r in source_sub)/len(source_sub),
            "answerable_non_answers":sum(r["terminal_status"]!="answered" for r in source_sub),
            "terminal_behavior_agreement_not_correctness":sum(d["terminal_behavior_agrees"] for d in detail)/len(detail),
            "latency_p50_seconds":float(np.percentile([r["wall_ms"]/1000 for r in sub],50)),
            "latency_p95_seconds":float(np.percentile([r["wall_ms"]/1000 for r in sub],95)),
            "task_wall_hours_sum":sum(r["wall_ms"] for r in sub)/3600000,
            "native_service_hours":sum(native_time)/3.6e12 if all(v is not None for v in native_time) else None,
            "native_service_time_note":"Sum of backend total_duration on the Metal-backed local model; not hardware GPU-active time.",
            "native_calls":len(calls),"input_tokens":input_tokens,"output_tokens":output_tokens,
            "tokens_per_trial":(input_tokens+output_tokens)/len(sub) if input_complete and output_complete else None,
            "tools_per_trial_mean":float(np.mean([r["ledger"]["tool_calls_count"] for r in sub])),
            "repairs_total":sum(r["ledger"]["repairs_count"] for r in sub),
            "trajectory_recall5":float(np.mean([r["retrieval"]["Recall@5"] for r in source_sub])),
            "trajectory_hit5":float(np.mean([r["retrieval"]["Hit@5"] for r in source_sub])),
            "trajectory_mrr":float(np.mean([r["retrieval"]["MRR"] for r in source_sub])),
            "citation_id_precision":float(np.mean([r["citation"]["citation_precision"] for r in source_sub])),
            "citation_id_recall":float(np.mean([r["citation"]["citation_recall"] for r in source_sub])),
            "reference_token_f1_diagnostic":float(np.mean([x["token_f1"] for x in reference])),
            "reference_exact_match_diagnostic":float(np.mean([x["normalized_exact_match"] for x in reference])),
            "lexical_unsupported_proxy_answered_only":float(np.mean([r["lexical_unsupported_proxy"] for r in answered])) if answered else None,
            "by_seed":by_seed,
            "budget_violations":[r["task_id"] for r in sub if r["ledger"]["tool_calls_count"]>manifest["config"]["budgets"]["max_tool_calls"]
                                 or r["ledger"]["repairs_count"]>manifest["config"]["budgets"]["max_repairs"]
                                 or r["ledger"]["step_count"]>manifest["config"]["budgets"]["max_steps"]]
        }
    result["details"]=details
    return result

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir",required=True)
    parser.add_argument("--tasks",required=True)
    parser.add_argument("--output",required=True)
    args=parser.parse_args()
    result=analyze(args.run_dir,args.tasks)
    with Path(args.output).open("x") as stream:
        json.dump(result,stream,ensure_ascii=False,indent=2)
    print(json.dumps({"trials":result["trials"],"modes":result["modes"]},ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
