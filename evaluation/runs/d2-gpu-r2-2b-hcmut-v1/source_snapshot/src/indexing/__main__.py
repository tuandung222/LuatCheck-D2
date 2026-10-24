"""CLI: python -m src.indexing {build,info,search,status}"""
from __future__ import annotations

import argparse
import json
import sys

from .builder import add_store, build_index, load_index, resolve_index_dir
from .config import load_config, parse_store
from .errors import IndexingError
from .manifest import read_manifest
from .vector_stores import backend_status


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m src.indexing", description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build", help="build an index from a YAML config")
    b.add_argument("--config", required=True)
    b.add_argument("--overwrite", action="store_true", help="delete and rebuild an existing index directory")
    i = sub.add_parser("info", help="print an index manifest")
    i.add_argument("index", help="index name under data/index/ or a directory")
    a = sub.add_parser("add-store", help="add a vector store to a built index by copying its numpy store (no re-embedding)")
    a.add_argument("--index", required=True)
    a.add_argument("--spec-json", required=True, help='e.g. \'{"backend": "faiss", "index_type": "hnsw", "name": "faiss_hnsw"}\'')
    s = sub.add_parser("search", help="query a built index")
    s.add_argument("index")
    s.add_argument("query")
    s.add_argument("-k", type=int, default=5)
    s.add_argument("--mode", choices=("hybrid", "keyword", "vector"), default="hybrid")
    s.add_argument("--store", help="vector store backend (name or backend; default: manifest default)")
    s.add_argument("--filter", action="append", default=[], metavar="FIELD=VALUE")
    s.add_argument("--no-verify-corpus", action="store_true")
    sub.add_parser("status", help="show which vector backends are installed")
    args = ap.parse_args(argv)

    try:
        if args.cmd == "status":
            print(json.dumps(backend_status(), indent=2, ensure_ascii=False))
        elif args.cmd == "build":
            cfg = load_config(args.config)
            manifest = build_index(cfg, overwrite=args.overwrite, log=lambda m: print(m, file=sys.stderr, flush=True))
            print(json.dumps({k: manifest[k] for k in ("name", "records", "chunks", "build_seconds")}, indent=2))
        elif args.cmd == "add-store":
            entry = add_store(args.index, parse_store(json.loads(args.spec_json)), log=lambda m: print(m, file=sys.stderr, flush=True))
            print(json.dumps({k: entry[k] for k in ("name", "backend", "count", "size_bytes")}))
        elif args.cmd == "info":
            print(json.dumps(read_manifest(resolve_index_dir(args.index)), indent=2, ensure_ascii=False))
        elif args.cmd == "search":
            flt = dict(f.split("=", 1) for f in args.filter) or None
            with load_index(args.index, verify_corpus=not args.no_verify_corpus, stores=[args.store] if args.store else None) as idx:
                for n, r in enumerate(idx.searcher(args.store).search(args.query, args.k, flt, args.mode), 1):
                    print(f"{n}. {r['doc_id']}  rrf={r['rrf_score']:.4f}  kw#{r['keyword_rank']} vec#{r['vector_rank']}  {r['title'][:80]}")
    except IndexingError as exc:
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
