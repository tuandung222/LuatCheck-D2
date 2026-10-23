"""Build an index (records + keyword index + vector stores + manifest) and load it back with staleness checks."""
from __future__ import annotations

import datetime as _dt
import json
import platform
import shutil
import sys
import time
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence

import numpy as np

from .chunking import Chunk, chunk_record
from .config import PROJECT_ROOT, IndexConfig, StoreSpec, load_config, resolve_path
from .embeddings import EmbeddingProvider, make_provider
from .errors import BackendError, ConfigError, IndexingError, StaleIndexError
from .hybrid import HybridSearcher
from .keyword import KeywordDoc, KeywordIndex, open_keyword_index
from .manifest import (FAILED_NAME, MANIFEST_NAME, SCHEMA_VERSION, check_provider_matches, read_manifest, rebuild_hint,
                       write_manifest)
from .records import RecordStore, load_corpus, sha256_file, vector_metadata
from .resources import peak_rss_mb
from .vector_stores import VectorStore, canonical_backend, open_store

EMBED_GROUP = 64  # chunks embedded then written to every store per step (bounds memory for large corpora)
_NON_DOC_FIELDS = ("chunk_index", "chunk_count", "char_start", "char_end")


def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")


def _store_path(index_dir: Path, spec: StoreSpec) -> Optional[Path]:
    if spec.params.get("url"):
        return None
    rel = Path(spec.path) if spec.path else Path("vector") / spec.name
    return rel if rel.is_absolute() else index_dir / rel


def _prepare_dir(index_dir: Path, overwrite: bool, output_root: Path) -> None:
    if index_dir.exists() and any(index_dir.iterdir()):
        if not overwrite:
            raise IndexingError(f"{index_dir} already exists; pass overwrite=True / --overwrite to rebuild it")
        # only ever delete something that is recognisably one of our index directories
        if not ((index_dir / MANIFEST_NAME).exists() or (index_dir / FAILED_NAME).exists()):
            raise IndexingError(f"refusing to overwrite {index_dir}: no {MANIFEST_NAME} found, it does not look like an index")
        if output_root not in index_dir.parents:
            raise IndexingError(f"refusing to delete {index_dir}: not inside the index output directory {output_root}")
        shutil.rmtree(index_dir)
    index_dir.mkdir(parents=True, exist_ok=True)


def _store_entry(st: VectorStore, spec: StoreSpec, index_dir: Path, write_seconds: float, expected: int) -> Dict[str, Any]:
    path = _store_path(index_dir, spec)
    entry = {"name": spec.name, "backend": spec.backend, "collection": spec.collection, "metric": spec.metric,
             "path": (str(path.relative_to(index_dir)) if path and index_dir in path.parents else (str(path) if path else None)),
             "params": spec.params, "count": st.count(), "size_bytes": st.size_on_disk(),
             "build_seconds_write": round(write_seconds, 3), "info": st.info()}
    if entry["count"] != expected:
        raise BackendError(f"{spec.name}: stored {entry['count']} vectors, expected {expected}")
    return entry


def _needs_separate_process(spec: StoreSpec, provider: EmbeddingProvider) -> bool:
    """FAISS cannot share a process with torch (duplicate libomp); see vector_stores/faiss_store.py."""
    return spec.backend == "faiss" and (provider.has_tokenizer or "torch" in sys.modules)


def _spec_to_json(spec: StoreSpec) -> str:
    return json.dumps({"backend": spec.backend, "name": spec.name, "collection": spec.collection, "metric": spec.metric,
                       "path": spec.path, **spec.params})


def add_store(index: str | Path, spec: StoreSpec, log: Optional[Callable[[str], None]] = None) -> Dict[str, Any]:
    """Add (or replace) a vector store in a built index by copying the vectors of its numpy store: no re-embedding.

    Runs without loading any embedding model, so it is also how FAISS stores are written next to a torch-based build.
    """
    log = log or (lambda m: None)
    index_dir = resolve_index_dir(index)
    manifest = read_manifest(index_dir)
    source = next((e for e in manifest["vector_stores"] if e["backend"] == "numpy" and e["name"] != spec.name), None)
    if source is None:
        raise ConfigError("add-store copies vectors from the index's numpy store; this index has none")
    src_path = Path(source["path"])
    src_path = src_path if src_path.is_absolute() else index_dir / src_path
    src = open_store("numpy", str(src_path), source["collection"], manifest["embedding"]["dimension"], source["metric"], mode="open")
    try:
        ids, matrix, metas = src.export()
    finally:
        src.close()
    spec_path = _store_path(index_dir, spec)
    st = open_store(spec.backend, str(spec_path) if spec_path else None, spec.collection, matrix.shape[1], spec.metric,
                    mode="overwrite", **spec.params)
    try:
        t0 = time.perf_counter()
        for s in range(0, len(ids), 1024):
            st.upsert(ids[s:s + 1024], matrix[s:s + 1024], metas[s:s + 1024])
        st.persist()
        entry = _store_entry(st, spec, index_dir, time.perf_counter() - t0, manifest["chunks"])
    finally:
        st.close()
    entry["copied_from"] = source["name"]
    manifest["vector_stores"] = [e for e in manifest["vector_stores"] if e["name"] != spec.name] + [entry]
    write_manifest(index_dir, manifest)
    log(f"added store {spec.name!r} ({spec.backend}): {entry['count']} vectors in {entry['build_seconds_write']}s")
    return entry


def _add_store_in_subprocess(index_dir: Path, spec: StoreSpec, log: Callable[[str], None]) -> None:
    import os
    import subprocess
    log(f"writing store {spec.name!r} in a separate process (cannot share a process with torch)")
    proc = subprocess.run([sys.executable, "-m", "src.indexing", "add-store", "--index", str(index_dir), "--spec-json", _spec_to_json(spec)],
                          cwd=PROJECT_ROOT, capture_output=True, text=True, env={**os.environ, "PYTHONPATH": str(PROJECT_ROOT)})
    if proc.returncode != 0:
        raise BackendError(f"add-store for {spec.name!r} failed (exit {proc.returncode}): {proc.stderr.strip()[-800:]}")


def build_index(cfg: IndexConfig, provider: Optional[EmbeddingProvider] = None, overwrite: bool = False,
                log: Optional[Callable[[str], None]] = None, close_provider: bool = False) -> Dict[str, Any]:
    """Build the index described by `cfg`; returns the manifest. A failed build leaves BUILD_FAILED.json
    (and whatever was written) in the index directory and re-raises; no partial index has a manifest."""
    log = log or (lambda m: None)
    index_dir = cfg.index_dir
    _prepare_dir(index_dir, overwrite, resolve_path(cfg.output_dir))
    t_start = time.perf_counter()
    own_provider = provider is None
    stores: List[VectorStore] = []
    keyword: Optional[KeywordIndex] = None
    records_store: Optional[RecordStore] = None
    try:
        # 1. corpora
        corpus_entries, records, seen = [], [], {}
        for spec in cfg.corpora:
            path = resolve_path(spec.path)
            recs = load_corpus(path, default_collection_id=spec.collection_id)
            for r in recs:
                if r["doc_id"] in seen:
                    raise ConfigError(f"duplicate doc_id {r['doc_id']!r} in {spec.path} and {seen[r['doc_id']]}")
                seen[r["doc_id"]] = spec.path
            records.extend(recs)
            corpus_entries.append({"path": spec.path, "sha256": sha256_file(path), "records": len(recs),
                                   "default_collection_id": spec.collection_id})
        log(f"corpora: {len(records)} records from {len(cfg.corpora)} file(s)")

        # 2. embedding provider + chunking
        provider = provider or make_provider(cfg.embedding)
        provider.load()
        offsets_fn = provider.token_offsets if provider.has_tokenizer else None
        chunks: List[Chunk] = []
        for rec in records:
            chunks.extend(chunk_record(rec, cfg.chunking, offsets_fn))
        multi = sum(1 for c in chunks if c.index == 0 and c.count > 1)
        log(f"chunking: {len(chunks)} chunks ({multi} records split); mode={'tokens' if offsets_fn else 'characters'}")
        rec_by_id = {r["doc_id"]: r for r in records}

        # 3. record store + keyword index
        records_store = RecordStore(index_dir / RecordStore.FILENAME)
        records_store.create(records)
        t0 = time.perf_counter()
        keyword = open_keyword_index(cfg.keyword_index, index_dir, mode="open_or_create")
        keyword.build([KeywordDoc(r["doc_id"], r["title"], r["content"], vector_metadata(r, cfg.vector_metadata_fields)) for r in records])
        keyword.persist()
        keyword_seconds = time.perf_counter() - t0
        log(f"keyword index [{keyword.backend}]: {keyword.count()} docs in {keyword_seconds:.2f}s")

        # 4. embed chunk groups and write every vector store
        dim = provider.dimension
        store_seconds = {s.name: 0.0 for s in cfg.vector_stores}
        deferred = [s for s in cfg.vector_stores if _needs_separate_process(s, provider)]
        active_specs = [s for s in cfg.vector_stores if s not in deferred]
        if deferred and not any(s.backend == "numpy" for s in active_specs):
            raise ConfigError(f"stores {[s.name for s in deferred]} are written in a separate process by copying the vectors of a "
                              "numpy store: add a numpy store to retrieval.vector_stores")
        embed_before = dict(provider.stats)
        t_embed0 = time.perf_counter()
        for g in range(0, len(chunks), EMBED_GROUP):
            group = chunks[g:g + EMBED_GROUP]
            vecs = provider.embed_documents([c.embed_text for c in group])
            if not stores:
                dim = int(vecs.shape[1])
                for spec in active_specs:
                    path = _store_path(index_dir, spec)
                    stores.append(open_store(spec.backend, str(path) if path else None, spec.collection, dim, spec.metric,
                                             mode="overwrite", **spec.params))
            ids = [c.chunk_id for c in group]
            metas = []
            for c in group:
                m = vector_metadata(rec_by_id[c.doc_id], cfg.vector_metadata_fields)
                m.update({"chunk_index": c.index, "chunk_count": c.count, "char_start": c.start, "char_end": c.end})
                metas.append(m)
            for st, spec in zip(stores, active_specs):
                t1 = time.perf_counter()
                st.upsert(ids, vecs, metas)
                store_seconds[spec.name] += time.perf_counter() - t1
            if (g // EMBED_GROUP) % 4 == 0:
                log(f"embedded {min(g + EMBED_GROUP, len(chunks))}/{len(chunks)} chunks")
        embed_wall = time.perf_counter() - t_embed0
        embed_seconds = provider.stats["seconds"] - embed_before["seconds"]
        embed_texts = provider.stats["texts"] - embed_before["texts"]
        if not stores:
            raise IndexingError("no chunks were produced; nothing to index")

        store_entries = []
        for st, spec in zip(stores, active_specs):
            t1 = time.perf_counter()
            st.persist()
            store_seconds[spec.name] += time.perf_counter() - t1
            store_entries.append(_store_entry(st, spec, index_dir, store_seconds[spec.name], len(chunks)))

        manifest = {
            "schema_version": SCHEMA_VERSION,
            "name": cfg.name,
            "built_at": _now(),
            "build_seconds": round(time.perf_counter() - t_start, 3),
            "config_path": cfg.source_path,
            "config": cfg.to_dict(),
            "corpora": corpus_entries,
            "records": len(records),
            "chunks": len(chunks),
            "chunking": cfg.chunking.as_dict(),
            "embedding": {
                "identity": provider.identity(),
                "config": cfg.embedding,
                "dimension": dim,
                "normalized": provider.normalize,
                "max_tokens": provider.max_tokens,
                "info": provider.info(),
                "texts_embedded": embed_texts,
                "embed_seconds": round(embed_seconds, 3),
                "embed_wall_seconds": round(embed_wall, 3),
                "texts_per_second": round(embed_texts / embed_seconds, 2) if embed_seconds > 0 else None,
            },
            "keyword": {"backend": keyword.backend, "config": cfg.keyword_index, "build_seconds": round(keyword_seconds, 3),
                        "info": keyword.info(), "size_bytes": (Path(keyword.info()["path"]).stat().st_size
                                                               if keyword.persistent else None)},
            "vector_stores": store_entries,
            "default_store": cfg.default_store or active_specs[0].name,
            "search": {"rrf_k": cfg.rrf_k, "candidates": cfg.candidates},
            "environment": {"python": sys.version.split()[0], "platform": platform.platform(), "machine": platform.machine(),
                            "process_peak_rss_mb": round(peak_rss_mb(), 1),
                            "provider_peak_memory_mb": getattr(provider, "memory_peak_seen_mb", None)},
        }
        write_manifest(index_dir, manifest)
        for st in stores:  # release file handles/locks before other processes touch the same stores
            st.close()
        stores = []
        for spec in deferred:
            _add_store_in_subprocess(index_dir, spec, log)
        if deferred:
            manifest = read_manifest(index_dir)
            order = {s.name: n for n, s in enumerate(cfg.vector_stores)}
            manifest["vector_stores"].sort(key=lambda e: order.get(e["name"], 99))
            manifest["build_seconds"] = round(time.perf_counter() - t_start, 3)
            write_manifest(index_dir, manifest)
        log(f"built {index_dir} in {manifest['build_seconds']}s")
        return manifest
    except BaseException as exc:
        try:
            index_dir.mkdir(parents=True, exist_ok=True)
            (index_dir / FAILED_NAME).write_text(
                __import__("json").dumps({"failed_at": _now(), "error": f"{type(exc).__name__}: {exc}",
                                          "traceback": traceback.format_exc()[-2000:]}, indent=2), encoding="utf-8")
        except OSError:
            pass
        raise
    finally:
        for st in stores:
            st.close()
        if keyword is not None:
            keyword.close()
        if records_store is not None:
            records_store.close()
        if own_provider or close_provider:
            if provider is not None:
                provider.close()


# =============================================================================================
# loading
# =============================================================================================
@dataclass
class LoadedIndex:
    index_dir: Path
    manifest: Dict[str, Any]
    records: RecordStore
    keyword: KeywordIndex
    stores: Dict[str, VectorStore]
    provider: EmbeddingProvider
    default_store: str

    def store(self, backend: Optional[str] = None) -> VectorStore:
        key = backend or self.default_store
        if key not in self.stores:
            try:
                key = canonical_backend(key)
            except ConfigError:
                pass
        if key not in self.stores:
            raise ConfigError(f"index {self.manifest['name']!r} has no opened store {key!r}; opened: {sorted(self.stores)}")
        return self.stores[key]

    def searcher(self, backend: Optional[str] = None, **kwargs: Any) -> HybridSearcher:
        search = self.manifest["search"]
        kwargs.setdefault("rrf_k", search["rrf_k"])
        kwargs.setdefault("candidates", search["candidates"])
        return HybridSearcher(self.keyword, self.store(backend), self.provider, self.records, **kwargs)

    def close(self) -> None:
        for st in self.stores.values():
            st.close()
        self.keyword.close()
        self.records.close()

    def __enter__(self) -> "LoadedIndex":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()


def resolve_index_dir(index: str | Path, output_dir: str = "data/index") -> Path:
    p = Path(index)
    if p.is_absolute() or len(p.parts) > 1 or p.exists():
        return p if p.is_absolute() else resolve_path(p)
    return resolve_path(output_dir) / str(index)


def verify_corpora(manifest: Dict[str, Any], corpus_paths: Optional[Sequence[str | Path]] = None) -> None:
    entries = manifest["corpora"]
    if corpus_paths is not None and len(corpus_paths) != len(entries):
        raise ConfigError(f"expected {len(entries)} corpus path(s), got {len(corpus_paths)}")
    for n, entry in enumerate(entries):
        path = resolve_path(corpus_paths[n] if corpus_paths is not None else entry["path"])
        if not path.is_file():
            raise StaleIndexError(f"corpus file {path} (hashed into the index) is missing. " + rebuild_hint(manifest))
        actual = sha256_file(path)
        if actual != entry["sha256"]:
            raise StaleIndexError(
                f"corpus {entry['path']} changed since the index was built (sha256 {actual[:12]}... != manifest {entry['sha256'][:12]}...). "
                + rebuild_hint(manifest)
            )


def load_index(index: str | Path, provider: Optional[EmbeddingProvider] = None, verify_corpus: bool = True,
               corpus_paths: Optional[Sequence[str | Path]] = None, stores: Optional[Sequence[str] | str] = None) -> LoadedIndex:
    """Open a built index. Raises StaleIndexError when the corpus hash or the embedding identity differs from
    the manifest, ManifestError when the build is missing/incomplete.

    `stores`: names of the vector stores to open; None opens only the manifest's default store, "all" opens every
    store (useful for comparing backends; FAISS cannot be opened in a process that has imported torch)."""
    index_dir = resolve_index_dir(index)
    manifest = read_manifest(index_dir)
    if verify_corpus:
        verify_corpora(manifest, corpus_paths)
    if provider is None:
        provider = make_provider(manifest["embedding"]["config"])
    check_provider_matches(manifest, provider.identity(), provider.dimension)

    entries = {e["name"]: e for e in manifest["vector_stores"]}
    if stores == "all":
        wanted = list(entries)
    elif stores:
        wanted = list(stores)
    else:
        wanted = [manifest["default_store"]]
    missing = [w for w in wanted if w not in entries]
    if missing:
        raise ConfigError(f"index {manifest['name']!r} was not built with store(s) {missing}; built with {sorted(entries)}")
    opened: Dict[str, VectorStore] = {}
    records = RecordStore(index_dir / RecordStore.FILENAME).open()
    keyword: Optional[KeywordIndex] = None
    try:
        for name in wanted:
            e = entries[name]
            path = Path(e["path"]) if e["path"] else None
            if path is not None and not path.is_absolute():
                path = index_dir / path
            opened[name] = open_store(e["backend"], str(path) if path else None, e["collection"], manifest["embedding"]["dimension"],
                                      e["metric"], mode="open", **e["params"])
            if opened[name].count() != e["count"]:
                raise StaleIndexError(f"{name}: {opened[name].count()} vectors on disk but the manifest says {e['count']}. "
                                      + rebuild_hint(manifest))
        kcfg = manifest["keyword"]["config"]
        keyword = open_keyword_index(kcfg, index_dir, mode="open")
        if not keyword.persistent:
            from .keyword import KeywordDoc
            keyword.build([KeywordDoc(r["doc_id"], r["title"], r["content"],
                                      {k: v for k, v in vector_metadata(r, manifest["config"].get("vector_metadata_fields")).items()})
                           for r in records])
        default = manifest["default_store"] if manifest["default_store"] in opened else wanted[0]
        return LoadedIndex(index_dir, manifest, records, keyword, opened, provider, default)
    except BaseException:
        for st in opened.values():
            st.close()
        if keyword is not None:
            keyword.close()
        records.close()
        raise
