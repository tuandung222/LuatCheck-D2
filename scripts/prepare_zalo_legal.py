"""Download and prepare GreenNode/zalo-ai-legal-text-retrieval-vn for LuatCheck indexing & retrieval evaluation.

Usage:
  PYTHONPATH=. .venv/bin/python scripts/prepare_zalo_legal.py [--out-dir data/benchmarks/zalo_legal]
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List

import pyarrow.parquet as pq
from huggingface_hub import hf_hub_download

REPO_ID = "GreenNode/zalo-ai-legal-text-retrieval-vn"


def download_and_prepare(out_dir: Path) -> Dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    corpus_pq = hf_hub_download(repo_id=REPO_ID, filename="corpus/test-00000-of-00001.parquet", repo_type="dataset")
    queries_pq = hf_hub_download(repo_id=REPO_ID, filename="queries/test-00000-of-00001.parquet", repo_type="dataset")
    qrels_pq = hf_hub_download(repo_id=REPO_ID, filename="qrels/test-00000-of-00001.parquet", repo_type="dataset")

    corpus_table = pq.read_table(corpus_pq)
    queries_table = pq.read_table(queries_pq)
    qrels_table = pq.read_table(qrels_pq)

    # 1. Qrels: query-id -> list of relevant corpus-ids (where score > 0)
    qrels_map: Dict[str, List[str]] = defaultdict(list)
    relevant_doc_ids = set()
    for row in qrels_table.to_pylist():
        qid = str(row["query-id"]).strip()
        cid = str(row["corpus-id"]).strip()
        score = float(row.get("score", 1))
        if score > 0 and cid not in qrels_map[qid]:
            qrels_map[qid].append(cid)
            relevant_doc_ids.add(cid)

    # 2. Queries: keep queries that have at least one positive relevant doc in test qrels
    queries: List[Dict[str, Any]] = []
    for row in queries_table.to_pylist():
        qid = str(row["id"]).strip()
        text = str(row["text"]).strip()
        if qid in qrels_map and text:
            queries.append({
                "query_id": qid,
                "query": text,
                "relevant_doc_ids": qrels_map[qid],
            })

    # 3. Full Corpus in LuatCheck record format
    corpus_records: List[Dict[str, Any]] = []
    for row in corpus_table.to_pylist():
        cid = str(row["id"]).strip()
        title = str(row.get("title") or "").strip()
        text = str(row.get("text") or "").strip()
        if not cid or not (title or text):
            continue
        if title and not text.startswith(title):
            content = f"{title}\n{text}".strip()
        else:
            content = text or title
        corpus_records.append({
            "doc_id": cid,
            "article_id": cid,
            "collection_id": "zalo_legal_vn",
            "source_name": "Zalo AI Legal Text Retrieval (GreenNode)",
            "title": title,
            "content": content,
        })

    corpus_path = out_dir / "corpus_full.json"
    queries_path = out_dir / "test_queries.json"
    corpus_path.write_text(json.dumps(corpus_records, ensure_ascii=False, indent=2), encoding="utf-8")
    queries_path.write_text(json.dumps(queries, ensure_ascii=False, indent=2), encoding="utf-8")

    # 4. Build a 2,000-article Hard-Negative + Gold subset for fast (<4 min) local Mac vector indexing:
    #    - All 447 gold relevant articles (100% coverage of all 818 test queries)
    #    - Top lexical confuser articles retrieved by SQLite FTS5 across all 61,425 articles for the 818 queries
    #    - Sibling articles from the same legal acts (same prefix before '_') up to 2,000 articles
    rec_by_id = {r["doc_id"]: r for r in corpus_records}
    selected_ids: List[str] = [cid for cid in sorted(relevant_doc_ids) if cid in rec_by_id]
    selected_set = set(selected_ids)

    from src.indexing.keyword import KeywordDoc, SqliteFts5Index
    fts_full_path = out_dir / "fts5_full_61k.sqlite"
    if fts_full_path.exists():
        fts_full_path.unlink()
    fts = SqliteFts5Index(path=str(fts_full_path), tokenizer="unicode61 remove_diacritics 0", title_weight=2.0, bigrams=True)
    fts.build([KeywordDoc(r["doc_id"], r["title"], r["content"], {}) for r in corpus_records])
    fts.persist()

    target_size = 1000
    # Add top-2 FTS5 hard negatives per query from the 61,425 corpus
    for q in queries:
        if len(selected_ids) >= target_size:
            break
        hits = fts.search(q["query"], k=3)
        for h in hits:
            if h.id not in selected_set and h.id in rec_by_id:
                selected_set.add(h.id)
                selected_ids.append(h.id)
                if len(selected_ids) >= target_size:
                    break
    fts.close()

    # Fill any remaining slots with sibling articles from the same legal acts
    gold_prefixes = {cid.rsplit("_", 1)[0] for cid in relevant_doc_ids if "_" in cid}
    for r in corpus_records:
        if len(selected_ids) >= target_size:
            break
        cid = r["doc_id"]
        if cid not in selected_set and "_" in cid and cid.rsplit("_", 1)[0] in gold_prefixes:
            selected_set.add(cid)
            selected_ids.append(cid)

    # Final fallback if still < target_size
    for r in corpus_records:
        if len(selected_ids) >= target_size:
            break
        cid = r["doc_id"]
        if cid not in selected_set:
            selected_set.add(cid)
            selected_ids.append(cid)

    eval_records = [rec_by_id[cid] for cid in selected_ids]
    eval_corpus_path = out_dir / "corpus_eval_hard2k.json"
    eval_corpus_path.write_text(json.dumps(eval_records, ensure_ascii=False, indent=2), encoding="utf-8")

    summary = {
        "dataset": REPO_ID,
        "corpus_records": len(corpus_records),
        "eval_hard2k_records": len(eval_records),
        "test_queries_with_qrels": len(queries),
        "total_qrel_pairs": sum(len(q["relevant_doc_ids"]) for q in queries),
        "unique_relevant_docs_in_test": len(relevant_doc_ids),
        "corpus_path": str(corpus_path),
        "eval_corpus_path": str(eval_corpus_path),
        "fts5_full_path": str(fts_full_path),
        "queries_path": str(queries_path),
    }
    (out_dir / "manifest.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-dir", default="data/benchmarks/zalo_legal", type=Path)
    args = ap.parse_args()
    summary = download_and_prepare(args.out_dir)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
