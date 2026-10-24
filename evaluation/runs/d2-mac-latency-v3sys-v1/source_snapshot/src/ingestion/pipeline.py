"""Config-driven build: sources -> loaders -> normalisation -> ruleset -> chunks -> validation -> corpus + manifest.

Determinism: nothing in the corpus or the manifest depends on wall-clock time, environment paths or hash
ordering. The manifest records input hashes, the resolved parameters, library versions, counts and warnings.
"""
from __future__ import annotations

import copy
import hashlib
import importlib.metadata
import json
import platform
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

from . import __version__
from .chunker import (IdContext, assign_ids, build_document_chunk, build_flat_chunks, build_tree_chunks,
                      resolve_chunking)
from .errors import ConfigError, IngestionError
from .loaders import detect_format, load_document
from .normalize import NormalizeConfig, normalize
from .rulesets import ParagraphRuleset, ascii_slug, get_ruleset
from .schema import RECORD_FIELDS, SCHEMA_VERSION, Chunk
from .validate import validate_corpus, validate_source

SOURCE_KEYS = {"path", "url", "format", "collection_id", "doc_code", "source_name", "title", "document_number",
               "issued_date", "version", "ruleset", "ruleset_options", "loader", "normalize", "chunking", "ids",
               "metadata", "metadata_from", "min_coverage"}
IDS_KEYS = {"prefix", "templates", "article_id_alias"}
TOP_KEYS = {"version", "output", "defaults", "sources"}
SCALAR_SOURCE_FIELDS = ("document_number", "issued_date", "version", "url", "source_name", "title")
TOOL_NAME = "luatcheck-ingestion"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _deep_merge(base: Dict[str, Any], over: Dict[str, Any]) -> Dict[str, Any]:
    out = copy.deepcopy(base)
    for k, v in over.items():
        out[k] = _deep_merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else copy.deepcopy(v)
    return out


def load_config(path: Path) -> Dict[str, Any]:
    path = Path(path)
    if not path.is_file():
        raise ConfigError(f"ingestion config not found: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ConfigError(f"{path}: top level must be a mapping")
    unknown = set(data) - TOP_KEYS
    if unknown:
        raise ConfigError(f"{path}: unknown top-level key(s) {sorted(unknown)}; known: {sorted(TOP_KEYS)}")
    if data.get("version", 1) != 1:
        raise ConfigError(f"{path}: unsupported config version {data.get('version')!r}")
    out = data.get("output") or {}
    if not isinstance(out, dict) or not out.get("corpus") or not out.get("manifest"):
        raise ConfigError(f"{path}: `output` needs `corpus` and `manifest` paths")
    if not data.get("sources"):
        raise ConfigError(f"{path}: `sources` must list at least one source")
    return data


def _lib_version(dist: str) -> Optional[str]:
    try:
        return importlib.metadata.version(dist)
    except importlib.metadata.PackageNotFoundError:
        return None


@dataclass
class BuildResult:
    chunks: List[Chunk]
    manifest: Dict[str, Any]
    ok: bool
    errors: List[str] = field(default_factory=list)

    @property
    def records(self) -> List[Dict[str, Any]]:
        return [c.to_record() for c in self.chunks]

    @property
    def corpus_text(self) -> str:
        return json.dumps(self.records, ensure_ascii=False, indent=2) + "\n"

    @property
    def manifest_text(self) -> str:
        return json.dumps(self.manifest, ensure_ascii=False, indent=2) + "\n"


def _resolve_metadata_from(spec: Dict[str, Any], root: Path) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Copy provenance fields from a JSON manifest produced by the collection step (never typed twice)."""
    cfg = spec["metadata_from"]
    allowed = {"file", "records_key", "match", "fields", "verify_sha256_field"}
    if set(cfg) - allowed or "file" not in cfg or "match" not in cfg or "fields" not in cfg:
        raise ConfigError(f"metadata_from needs file, match, fields (optional: records_key, verify_sha256_field); got {sorted(cfg)}")
    path = root / cfg["file"]
    if not path.is_file():
        raise ConfigError(f"metadata_from file not found: {cfg['file']}")
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = data[cfg["records_key"]] if cfg.get("records_key") else data
    matches = [r for r in rows if all(r.get(k) == v for k, v in cfg["match"].items())]
    if len(matches) != 1:
        raise ConfigError(f"metadata_from {cfg['file']}: expected exactly one row matching {cfg['match']}, found {len(matches)}")
    row = matches[0]
    values = {}
    for out_key, src_key in cfg["fields"].items():
        if src_key not in row:
            raise ConfigError(f"metadata_from {cfg['file']}: row has no field {src_key!r}")
        values[out_key] = row[src_key]
    info = {"file": cfg["file"], "file_sha256": sha256_file(path), "match": cfg["match"],
            "fields": cfg["fields"]}
    if cfg.get("verify_sha256_field"):
        info["recorded_sha256"] = row.get(cfg["verify_sha256_field"])
    return values, info


def _build_source(index: int, spec: Dict[str, Any], root: Path) -> Tuple[List[Chunk], Dict[str, Any]]:
    unknown = set(spec) - SOURCE_KEYS
    if unknown:
        raise ConfigError(f"source {index}: unknown key(s) {sorted(unknown)}; known: {sorted(SOURCE_KEYS)}")
    if not spec.get("path"):
        raise ConfigError(f"source {index}: `path` is required")
    spec = copy.deepcopy(spec)
    meta_info = None
    if spec.get("metadata_from"):
        values, meta_info = _resolve_metadata_from(spec, root)
        for key, value in values.items():
            if key in SCALAR_SOURCE_FIELDS or key in ("collection_id", "doc_code"):
                spec.setdefault(key, value)  # explicit source keys win over the collection manifest
            else:
                spec.setdefault("metadata", {}).setdefault(key, value)
    path = root / spec["path"]
    if not path.is_file():
        raise IngestionError(f"source {index}: file not found: {spec['path']}")
    fmt = detect_format(path, spec.get("format"))
    file_sha = sha256_file(path)
    if meta_info and meta_info.get("recorded_sha256") and meta_info["recorded_sha256"] != file_sha:
        raise IngestionError(
            f"source {index} ({spec['path']}): sha256 {file_sha} differs from the {meta_info['recorded_sha256']} "
            f"recorded in {meta_info['file']}; refusing to attach that provenance to a different file")
    doc_code = spec.get("doc_code") or ascii_slug(path.stem)
    ids_cfg = spec.get("ids") or {}
    if set(ids_cfg) - IDS_KEYS:
        raise ConfigError(f"source {index}: unknown ids key(s) {sorted(set(ids_cfg) - IDS_KEYS)}; known: {sorted(IDS_KEYS)}")
    ruleset = get_ruleset(spec.get("ruleset") or "", spec.get("ruleset_options"))
    cfg = resolve_chunking(ruleset, spec.get("chunking"))
    norm_cfg = NormalizeConfig.from_dict(spec.get("normalize"))
    extra = dict(spec.get("metadata") or {})
    reserved = set(RECORD_FIELDS) | {"article_id"}
    if reserved & set(extra):
        raise ConfigError(f"source {index}: metadata key(s) {sorted(reserved & set(extra))} collide with schema fields")

    loaded = load_document(path, fmt, spec.get("loader"))
    norm = normalize(loaded, norm_cfg)
    if not norm.text.strip():
        raise IngestionError(f"source {index} ({spec['path']}): no text left after normalisation")
    title = spec.get("title") or spec.get("source_name") or path.stem
    source_name = spec.get("source_name") or title

    extraction = _extraction_label(fmt, loaded.info, norm_cfg, ruleset, cfg)
    base = dict(collection_id=spec.get("collection_id") or doc_code, source_name=source_name, source_sha256=file_sha,
                source_url=spec.get("url"), document_number=spec.get("document_number"),
                issued_date=str(spec["issued_date"]) if spec.get("issued_date") is not None else None,
                version=str(spec["version"]) if spec.get("version") is not None else None,
                doc_code=doc_code, extraction=extraction, extra=extra)
    ids = IdContext(ruleset, ids_cfg.get("templates"), ids_cfg.get("prefix", ""), doc_code,
                    list(ruleset.options.get("series_tags", [])) if hasattr(ruleset, "options") else [])
    alias = bool(ids_cfg.get("article_id_alias"))

    parse_stats: Dict[str, Any] = {}
    r_errors: List[str] = []
    r_warnings: List[str] = []
    fallback = None
    if isinstance(ruleset, ParagraphRuleset):
        chunks = build_flat_chunks(norm, ruleset, cfg, base, ids, title, alias)
    elif cfg["granularity"] == "document":
        chunks = build_document_chunk(norm, cfg, base, ids.format("document"), title, alias)
    else:
        result = ruleset.parse(norm.text, title)
        parse_stats = result.stats
        assign_ids(result, ids, title)
        r_errors, r_warnings = ruleset.validate(result)
        chunks = build_tree_chunks(norm, result, cfg, base, alias)
        if not any(not c.doc_id.endswith(("_lead", "_preamble")) for c in chunks):
            mode = cfg["on_no_structure"]
            if mode == "error":
                raise IngestionError(
                    f"source {index} ({spec['path']}): ruleset {ruleset.name!r} found no structure to chunk at "
                    f"granularity {cfg['granularity']!r}. Choose a different ruleset/granularity or set "
                    "chunking.on_no_structure to 'document' or 'paragraph'.")
            fallback = mode
            if mode == "document":
                chunks = build_document_chunk(norm, cfg, base, ids.format("document"), title, alias)
            else:
                para = ParagraphRuleset(cfg["fallback_paragraph"])
                para_ids = IdContext(para, None, ids.prefix, doc_code, [])
                chunks = build_flat_chunks(norm, para, {**cfg, "content_whitespace": cfg["content_whitespace"]}, base,
                                           para_ids, title, alias)
            r_warnings.append(f"no structure found; fell back to {mode} chunking")

    validation = validate_source(norm, chunks, cfg["content_whitespace"], r_errors, r_warnings,
                                 spec.get("min_coverage"))
    by_level: Dict[str, int] = {}
    for c in chunks:
        by_level[c.level] = by_level.get(c.level, 0) + 1
    rejected = parse_stats.get("rejected_markers", {})
    for kind, info in rejected.items():
        validation["warnings"].append(
            f"{info['count']} {kind} marker line(s) rejected as out of sequence/context and kept as text; e.g. {info['samples'][:2]}")
    for w in norm.warnings:
        validation["warnings"].append(w)
    manifest = {
        "index": index,
        "path": spec["path"],
        "sha256": file_sha,
        "bytes": path.stat().st_size,
        "format": fmt,
        "doc_code": doc_code,
        "collection_id": base["collection_id"],
        "source_name": source_name,
        "url": base["source_url"],
        "document_number": base["document_number"],
        "issued_date": base["issued_date"],
        "version": base["version"],
        "ruleset": ruleset.name,
        "ruleset_options": ruleset.options,
        "loader": {"options": spec.get("loader") or {}, "info": loaded.info},
        "normalize": asdict(norm_cfg),
        "chunking": cfg,
        "ids": {"prefix": ids.prefix, "templates": ids.templates, "article_id_alias": alias},
        "metadata_from": meta_info,
        "extraction": extraction,
        "pages": len([p for p, _, _ in norm.page_spans if p is not None]),
        "normalized_chars": len(norm.text),
        "normalized_sha256": sha256_bytes(norm.text.encode("utf-8")),
        "removed_lines": norm.removed[:40],
        "removed_lines_total": sum(r["count"] for r in norm.removed),
        "parse": parse_stats,
        "fallback_chunking": fallback,
        "counts": {"records": len(chunks), "by_level": dict(sorted(by_level.items()))},
        "validation": validation,
    }
    return chunks, manifest


def _extraction_label(fmt, info, norm_cfg: NormalizeConfig, ruleset, cfg) -> str:
    loader = {"pdf": f"pypdf extraction_mode={info.get('pypdf_mode', 'layout')}", "docx": "python-docx body paragraphs+tables",
              "html": "html.parser visible text", "markdown": "markdown text", "text": "plain text"}[fmt]
    steps = ["NFC", "whitespace folded per line"]
    if norm_cfg.remove_repeated_edges:
        steps.append("repeated running headers/footers removed")
    g = cfg.get("granularity")
    return (f"src.ingestion {__version__}: {loader}; {'; '.join(steps)}; ruleset={ruleset.name}"
            + (f"; granularity={g}" if g is not None else "") + f"; content_whitespace={cfg['content_whitespace']}")


def build(config_path: Path, root: Optional[Path] = None) -> BuildResult:
    config_path = Path(config_path)
    root = Path(root) if root is not None else Path.cwd()
    cfg_path = config_path if config_path.is_absolute() or config_path.exists() else root / config_path
    config = load_config(cfg_path)
    defaults = config.get("defaults") or {}
    chunks: List[Chunk] = []
    sources: List[Dict[str, Any]] = []
    for i, raw in enumerate(config["sources"]):
        spec = _deep_merge(defaults, raw)
        src_chunks, src_manifest = _build_source(i, spec, root)
        chunks.extend(src_chunks)
        sources.append(src_manifest)
    errors = [f"source {m['index']} ({m['path']}): {e}" for m in sources for e in m["validation"]["errors"]]
    errors += validate_corpus(chunks)
    warnings = [f"source {m['index']} ({m['path']}): {w}" for m in sources for w in m["validation"]["warnings"]]
    libs = {"PyYAML": _lib_version("PyYAML")}
    for fmt, dist in (("pdf", "pypdf"), ("docx", "python-docx")):
        if any(s["format"] == fmt for s in sources):
            libs[dist] = _lib_version(dist)
    by_level: Dict[str, int] = {}
    for c in chunks:
        by_level[c.level] = by_level.get(c.level, 0) + 1
    out = config["output"]
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "tool": {"name": TOOL_NAME, "version": __version__},
        "status": "ok" if not errors else "failed",
        "config": {"path": str(config_path), "sha256": sha256_file(cfg_path), "output": out,
                   "defaults": defaults},
        "environment": {"python": platform.python_version(), "libraries": libs},
        "sources": sources,
        "totals": {"sources": len(sources), "records": len(chunks), "by_level": dict(sorted(by_level.items()))},
        "errors": errors,
        "warnings": warnings,
        "output": {"corpus": out["corpus"], "records": len(chunks),
                   "corpus_sha256": sha256_bytes((json.dumps([c.to_record() for c in chunks], ensure_ascii=False, indent=2) + "\n").encode("utf-8"))},
    }
    return BuildResult(chunks, manifest, not errors, errors)


def _is_untouched_ingestion_output(corpus: Path, manifest: Path) -> bool:
    if not manifest.is_file():
        return False
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
        return (data.get("tool", {}).get("name") == TOOL_NAME
                and data.get("output", {}).get("corpus_sha256") == sha256_file(corpus))
    except (ValueError, OSError):
        return False


def write_outputs(result: BuildResult, root: Path, overwrite: bool = False) -> Tuple[Optional[Path], Path]:
    """Write the manifest always (a failed build is evidence too); write the corpus only when validation passed.
    A corpus file that exists and is not an untouched output of this tool is never overwritten unless
    `overwrite=True` - this protects hand-built or frozen corpora."""
    out = result.manifest["config"]["output"]
    corpus_path, manifest_path = root / out["corpus"], root / out["manifest"]
    if result.ok and corpus_path.exists() and not overwrite and not _is_untouched_ingestion_output(corpus_path, manifest_path):
        raise IngestionError(
            f"refusing to overwrite {out['corpus']}: it exists and is not an unmodified output of this tool "
            "(no matching manifest). Pick a new output path, or pass --overwrite if replacing it is intended.")
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    written = None
    if result.ok:
        corpus_path.parent.mkdir(parents=True, exist_ok=True)
        corpus_path.write_text(result.corpus_text, encoding="utf-8")
        written = corpus_path
    manifest_path.write_text(result.manifest_text, encoding="utf-8")
    return written, manifest_path
