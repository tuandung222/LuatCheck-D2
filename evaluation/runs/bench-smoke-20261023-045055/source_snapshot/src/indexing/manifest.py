"""Index manifest: what an index was built from, so a stale index is detected instead of silently used."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from .errors import ManifestError, StaleIndexError

MANIFEST_NAME = "manifest.json"
FAILED_NAME = "BUILD_FAILED.json"
SCHEMA_VERSION = 1


def read_manifest(index_dir: Path) -> Dict[str, Any]:
    mp = index_dir / MANIFEST_NAME
    failed = index_dir / FAILED_NAME
    if mp.is_file() and failed.is_file():
        raise ManifestError(f"{index_dir}: a build failed after the manifest was written ({failed.read_text(encoding='utf-8')[:300]}); rebuild the index")
    if not mp.is_file():
        failed = index_dir / FAILED_NAME
        hint = f" (a failed build left {failed}: {failed.read_text(encoding='utf-8')[:300]})" if failed.is_file() else ""
        raise ManifestError(f"no manifest at {mp}: the index is missing or its build did not finish{hint}")
    try:
        manifest = json.loads(mp.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise ManifestError(f"{mp} is not valid JSON: {exc}") from exc
    if manifest.get("schema_version") != SCHEMA_VERSION:
        raise ManifestError(f"{mp}: schema_version {manifest.get('schema_version')!r} != {SCHEMA_VERSION}; rebuild the index")
    return manifest


def write_manifest(index_dir: Path, manifest: Dict[str, Any]) -> None:
    mp = index_dir / MANIFEST_NAME
    tmp = mp.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(mp)


def rebuild_hint(manifest: Dict[str, Any]) -> str:
    src = manifest.get("config_path") or "<index.yaml>"
    return f"rebuild with: python -m src.indexing build --config {src} --overwrite"


def check_provider_matches(manifest: Dict[str, Any], identity: Dict[str, Any], dimension: int | None) -> None:
    built = manifest["embedding"]["identity"]
    diffs = {k: (built.get(k), identity.get(k)) for k in set(built) | set(identity) if built.get(k) != identity.get(k)}
    if diffs:
        raise StaleIndexError(
            "embedding provider does not match the index manifest "
            + "; ".join(f"{k}: built with {a!r}, now {b!r}" for k, (a, b) in sorted(diffs.items()))
            + ". " + rebuild_hint(manifest)
        )
    built_dim = manifest["embedding"]["dimension"]
    if dimension is not None and dimension != built_dim:
        raise StaleIndexError(f"embedding dimension {dimension} != manifest dimension {built_dim}. " + rebuild_hint(manifest))
