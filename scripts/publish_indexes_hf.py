"""Upload built 128-d google/embeddinggemma-2 LuatCheck indexes and benchmark results to Hugging Face Hub.

Usage:
  HF_TOKEN=... PYTHONPATH=. .venv/bin/python scripts/publish_indexes_hf.py \
      --repo-id tuandunghcmut/luatcheck-embeddinggemma2-128d-indexes
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import List

from huggingface_hub import HfApi

INDEX_NAMES: List[str] = [
    "labor_code_2019_gemma2_128d",
    "labour_vi_v1_gemma2_128d",
    "hcmut_academic_v1_gemma2_128d",
    "zalo_legal_gemma2_128d",
]


def build_readme(results_path: Path) -> str:
    results = json.loads(results_path.read_text(encoding="utf-8")) if results_path.exists() else {}
    lines = [
        "---",
        "license: apache-2.0",
        "language:",
        "- vi",
        "tags:",
        "- legal-retrieval",
        "- vietnamese",
        "- embeddinggemma-2",
        "- matryoshka-128d",
        "- faiss",
        "- qdrant",
        "- sqlite-fts5",
        "- luatcheck",
        "---",
        "",
        "# LuatCheck 128-d Vector & Hybrid Indexes (`google/embeddinggemma-2`)",
        "",
        "Bộ chỉ mục vector 128 chiều (Matryoshka Representation Learning `truncate_dim=128`) kết hợp từ khóa (`SQLite FTS5`) được xây dựng bằng mô hình [`google/embeddinggemma-2`](https://huggingface.co/google/embeddinggemma-2) (nhánh văn bản 270M tham số, `bfloat16`) cho hệ thống **LuatCheck**.",
        "",
        "## Danh sách các bộ Index trong Repository",
        "",
        "| Thư mục Index | Tập văn bản gốc | Số bản ghi (Records) | Số đoạn (Chunks) | Các Vector Stores đi kèm |",
        "|---|---|---:|---:|---|",
    ]
    for name in INDEX_NAMES:
        manifest_file = Path("data/index") / name / "manifest.json"
        if manifest_file.exists():
            m = json.loads(manifest_file.read_text(encoding="utf-8"))
            stores = ", ".join(f"`{s['name']}` ({s['backend']})" for s in m.get("vector_stores", []))
            corpus_path = m["corpora"][0]["path"] if m.get("corpora") else ""
            lines.append(f"| `{name}/` | `{corpus_path}` | {m['records']} | {m['chunks']} | {stores} + `sqlite_fts5` |")

    lines.extend([
        "",
        "## Kết quả thực nghiệm (Retrieval Benchmark)",
        "",
    ])

    for b_key, b_data in (results.get("benchmarks") or {}).items():
        lines.append(f"### {b_data.get('benchmark', b_key)} (`n = {b_data.get('queries_evaluated', 0)}` truy vấn)")
        lines.append("")
        lines.append("| Phương pháp | Recall@1 (%) | Recall@5 (%) | Recall@10 (%) | Recall@20 (%) | MRR@10 (%) | NDCG@10 (%) | MAP@10 (%) | Latency (ms/q) |")
        lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
        for m_name, metrics in (b_data.get("methods") or {}).items():
            lat = metrics.get("latency_ms_per_query", metrics.get("total_ms_per_query", "-"))
            lines.append(
                f"| `{m_name}` | {metrics.get('Recall@1', 0):.2f} | {metrics.get('Recall@5', 0):.2f} | "
                f"{metrics.get('Recall@10', 0):.2f} | {metrics.get('Recall@20', 0):.2f} | "
                f"{metrics.get('MRR@10', 0):.2f} | {metrics.get('NDCG@10', 0):.2f} | "
                f"{metrics.get('MAP@10', 0):.2f} | {lat} |"
            )
        lines.append("")

    lines.extend([
        "## Cách nạp và sử dụng trong LuatCheck",
        "",
        "```python",
        "from src.indexing.builder import load_index",
        "",
        "with load_index('data/index/labor_code_2019_gemma2_128d', stores=['numpy', 'qdrant']) as idx:",
        "    searcher = idx.searcher('numpy')",
        "    hits = searcher.search('thời gian thử việc tối đa trình độ cao đẳng trở lên', top_k=5, mode='hybrid')",
        "```",
        "",
    ])
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo-id", default="tuandunghcmut/luatcheck-embeddinggemma2-128d-indexes")
    ap.add_argument("--repo-type", default="dataset", choices=["dataset", "model"])
    args = ap.parse_args()

    token = os.environ.get("HF_TOKEN")
    if not token:
        raise RuntimeError("HF_TOKEN environment variable is required")

    api = HfApi(token=token)
    url = api.create_repo(repo_id=args.repo_id, repo_type=args.repo_type, private=False, exist_ok=True)
    print(f"Created/verified public {args.repo_type} repo: {url}")

    results_path = Path("data/benchmarks/zalo_legal/retrieval_comparison_results.json")
    readme_text = build_readme(results_path)
    readme_tmp = Path("data/index/_HF_README.md")
    readme_tmp.write_text(readme_text, encoding="utf-8")

    api.upload_file(
        path_or_fileobj=str(readme_tmp),
        path_in_repo="README.md",
        repo_id=args.repo_id,
        repo_type=args.repo_type,
        commit_message="Update README and benchmark tables",
    )
    readme_tmp.unlink()

    if results_path.exists():
        api.upload_file(
            path_or_fileobj=str(results_path),
            path_in_repo="benchmarks/retrieval_comparison_results.json",
            repo_id=args.repo_id,
            repo_type=args.repo_type,
            commit_message="Upload retrieval comparison results",
        )

    for name in INDEX_NAMES:
        idx_dir = Path("data/index") / name
        if not idx_dir.exists():
            continue
        print(f"Uploading {idx_dir} -> {args.repo_id}:{name}/ ...")
        api.upload_folder(
            folder_path=str(idx_dir),
            path_in_repo=name,
            repo_id=args.repo_id,
            repo_type=args.repo_type,
            ignore_patterns=["*.lock", "_eval_qvecs.npy", "__pycache__/*"],
            commit_message=f"Upload 128-d index {name}",
        )
    print(f"Successfully published all indexes to https://huggingface.co/datasets/{args.repo_id}")


if __name__ == "__main__":
    main()
