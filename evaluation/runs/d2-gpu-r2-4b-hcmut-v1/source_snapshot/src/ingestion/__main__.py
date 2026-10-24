"""CLI: python -m src.ingestion build --config config/ingestion/<name>.yaml [--root DIR] [--check] [--overwrite]"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .errors import IngestionError
from .pipeline import build, sha256_file, write_outputs


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="python -m src.ingestion", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    b = sub.add_parser("build", help="build the corpus and manifest described by an ingestion YAML")
    b.add_argument("--config", required=True, type=Path)
    b.add_argument("--root", type=Path, default=Path.cwd(), help="directory that source/output paths are relative to")
    b.add_argument("--check", action="store_true",
                   help="rebuild in memory and compare with the files on disk instead of writing (exit 1 on difference)")
    b.add_argument("--overwrite", action="store_true", help="allow replacing a corpus file this tool did not write")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    try:
        result = build(args.config, root)
        out = result.manifest["config"]["output"]
        if args.check:
            corpus, manifest = root / out["corpus"], root / out["manifest"]
            same = (result.ok and corpus.is_file() and manifest.is_file()
                    and corpus.read_text(encoding="utf-8") == result.corpus_text
                    and manifest.read_text(encoding="utf-8") == result.manifest_text)
            print("up to date" if same else "DIFFERENT or missing: rebuild with `build` (without --check)")
            return 0 if same else 1
        written, manifest_path = write_outputs(result, root, overwrite=args.overwrite)
    except IngestionError as exc:
        print(f"ingestion error: {exc}", file=sys.stderr)
        return 2
    totals = result.manifest["totals"]
    print(f"status={result.manifest['status']} sources={totals['sources']} records={totals['records']} "
          f"by_level={totals['by_level']}")
    print(f"manifest: {manifest_path.relative_to(root) if manifest_path.is_relative_to(root) else manifest_path}")
    if written:
        print(f"corpus:   {written.relative_to(root) if written.is_relative_to(root) else written} "
              f"sha256={sha256_file(written)}")
    for w in result.manifest["warnings"][:10]:
        print(f"warning: {w}", file=sys.stderr)
    if len(result.manifest["warnings"]) > 10:
        print(f"... {len(result.manifest['warnings']) - 10} more warning(s) in the manifest", file=sys.stderr)
    for e in result.errors[:20]:
        print(f"ERROR: {e}", file=sys.stderr)
    if not result.ok:
        print("validation failed: corpus not written (manifest written)", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
