"""Replay a run's own tool calls through the snapshot tools and the current tools (no inference).

Reports observation size and whether each task's reference excerpt is visible in the search snippet
of its gold article. Repeated queries and re-read articles count as the short notice the current loop sends.
"""
import argparse
import importlib.util
import json
from pathlib import Path

from src.tools.domain_tools import DomainKnowledgeRegistry

DUPLICATE_SEARCH_NOTICE = 230
DUPLICATE_ARTICLE_NOTICE = 170


def snapshot_registry(run_dir):
    path = Path(run_dir) / "source_snapshot/src/tools/domain_tools.py"
    spec = importlib.util.spec_from_file_location("snapshot_domain_tools", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.DomainKnowledgeRegistry()


def measure(run_dir, tasks_file):
    old, new = snapshot_registry(run_dir), DomainKnowledgeRegistry()
    tasks = {t["task_id"]: t for t in json.loads(Path(tasks_file).read_text())}
    size = lambda d: len(json.dumps(d, ensure_ascii=False))
    out = {"old_chars": 0, "new_chars": 0, "duplicate_notices": 0, "gold_hits": 0, "old_visible": 0, "new_visible": 0}
    for line in (Path(run_dir) / "runs.jsonl").read_text().splitlines():
        row = json.loads(line)
        queries, articles = set(), set()
        gold = tasks[row["task_id"]].get("reference_evidence") or []
        for call in row["ledger"]["llm_calls"]:
            action = call.get("response") or {}
            args = action.get("tool_args") or {}
            if action.get("action") == "search_law":
                query = args.get("query") or row["ledger"]["original_query"]
                top_k = max(1, min(int(args.get("top_k", 3) or 3), 5))
                before = old.search_law(query, top_k=top_k)
                out["old_chars"] += size(before)
                key = " ".join(query.lower().split())
                if key in queries:
                    out["duplicate_notices"] += 1
                    out["new_chars"] += DUPLICATE_SEARCH_NOTICE
                    continue
                queries.add(key)
                after = new.search_law(query, top_k=top_k)
                out["new_chars"] += size(after)
                for evidence in gold:
                    for a, b in zip(before["articles"], after["articles"]):
                        if a["article_id"] == evidence["article_id"]:
                            out["gold_hits"] += 1
                            out["old_visible"] += evidence["exact_quote"][:60] in a["content_snippet"]
                            out["new_visible"] += evidence["exact_quote"][:60] in b["content_snippet"]
            elif action.get("action") == "get_article":
                article_id = args.get("article_id", "")
                out["old_chars"] += size(old.get_article(article_id))
                if article_id.lower() in articles:
                    out["duplicate_notices"] += 1
                    out["new_chars"] += DUPLICATE_ARTICLE_NOTICE
                    continue
                articles.add(article_id.lower())
                out["new_chars"] += size(new.get_article(article_id))
    out["reduction"] = 1 - out["new_chars"] / out["old_chars"]
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", default="evaluation/runs/bll2019-main-v2")
    parser.add_argument("--tasks", default="evaluation/benchmarks/bll2019_v1/tasks.json")
    args = parser.parse_args()
    print(json.dumps(measure(args.run_dir, args.tasks), indent=2))


if __name__ == "__main__":
    main()
