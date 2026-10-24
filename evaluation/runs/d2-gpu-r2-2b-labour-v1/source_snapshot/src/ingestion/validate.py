"""Validation of built chunks against the normalised source text.

Checks (errors fail the build; warnings are recorded in the manifest):
  * ids unique within the corpus (checked across all sources by `validate_corpus`), non-empty ids/titles/content
  * each chunk's content is found verbatim in the normalised source text - twice: the recorded
    [char_start, char_end) slice must equal the content, and the content must also be found by plain
    substring search. With `content_whitespace: collapse` both checks compare whitespace-folded text.
  * levels are valid, offsets are in range, page numbers exist
  * coverage: fraction of source characters (and of non-whitespace characters) inside at least one chunk,
    plus the uncovered stretches that contain text
  * ruleset checks (e.g. contiguous article numbering for vi_legal)
"""
from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .normalize import NormalizedDocument
from .schema import Chunk, LEVELS

MAX_LISTED_GAPS = 25


def _fold(s: str) -> str:
    return " ".join(s.split())


def coverage_report(text: str, spans: Sequence[Tuple[int, int]]) -> Dict[str, Any]:
    n = len(text)
    merged: List[List[int]] = []
    for s, e in sorted(spans):
        if merged and s <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])
    nonws = [0] * (n + 1)
    for i, ch in enumerate(text):
        nonws[i + 1] = nonws[i] + (0 if ch.isspace() else 1)
    total_nonws = nonws[n]
    covered_chars = sum(e - s for s, e in merged)
    covered_nonws = sum(nonws[e] - nonws[s] for s, e in merged)
    gaps: List[Dict[str, Any]] = []
    cursor = 0
    for s, e in merged + [[n, n]]:
        if s > cursor and nonws[s] - nonws[cursor] > 0:
            seg = text[cursor:s].strip()
            gaps.append({"start": cursor, "end": s, "non_whitespace_chars": nonws[s] - nonws[cursor],
                         "preview": _fold(seg)[:100]})
        cursor = max(cursor, e)
    return {
        "source_chars": n,
        "covered_chars": covered_chars,
        "char_fraction": round(covered_chars / n, 6) if n else 0.0,
        "source_non_whitespace_chars": total_nonws,
        "covered_non_whitespace_chars": covered_nonws,
        "non_whitespace_fraction": round(covered_nonws / total_nonws, 6) if total_nonws else 0.0,
        "uncovered_stretches_with_text": len(gaps),
        "uncovered_listed": gaps[:MAX_LISTED_GAPS],
    }


def validate_source(norm: NormalizedDocument, chunks: Sequence[Chunk], content_whitespace: str,
                    ruleset_errors: Sequence[str], ruleset_warnings: Sequence[str],
                    min_coverage: Optional[float] = None, max_title_chars: int = 250) -> Dict[str, Any]:
    text = norm.text
    folded_text = _fold(text) if content_whitespace == "collapse" else text
    errors: List[str] = list(ruleset_errors)
    warnings: List[str] = list(ruleset_warnings)
    counts = Counter()
    page_numbers = {p for p, _, _ in norm.page_spans if p is not None}
    ids = {c.doc_id for c in chunks}
    for i, c in enumerate(chunks):
        where = f"chunk {i} ({c.doc_id!r})"
        if not c.doc_id:
            errors.append(f"{where}: empty doc_id")
        if not c.title.strip():
            errors.append(f"{where}: empty title")
        if not c.content.strip():
            errors.append(f"{where}: empty content")
            continue
        if c.level not in LEVELS:
            errors.append(f"{where}: invalid level {c.level!r}")
        if not (0 <= c.char_start < c.char_end <= len(text)):
            errors.append(f"{where}: offsets [{c.char_start}, {c.char_end}) outside the normalised text")
            continue
        piece = text[c.char_start:c.char_end]
        piece = _fold(piece) if content_whitespace == "collapse" else piece
        if piece != c.content:
            errors.append(f"{where}: content differs from the normalised text slice at its offsets")
            counts["slice_mismatch"] += 1
        elif c.content not in folded_text:
            errors.append(f"{where}: content not found verbatim in the normalised source text")
            counts["not_found"] += 1
        else:
            counts["verbatim"] += 1
        if len(c.title) > max_title_chars:
            warnings.append(f"{where}: title is {len(c.title)} chars; the heading may have absorbed body text")
        bad_pages = [p for p in c.source_pages if p not in page_numbers]
        if bad_pages:
            errors.append(f"{where}: source_pages {bad_pages} are not pages of the source")
        if c.parent_id and c.parent_id not in ids:
            counts["parent_not_emitted"] += 1
    cov = coverage_report(text, [(c.char_start, c.char_end) for c in chunks if 0 <= c.char_start < c.char_end <= len(text)])
    if min_coverage is not None and cov["non_whitespace_fraction"] < min_coverage:
        errors.append(f"non-whitespace coverage {cov['non_whitespace_fraction']:.4f} is below min_coverage {min_coverage}")
    return {
        "chunks": len(chunks),
        "verbatim_chunks": counts["verbatim"],
        "chunks_with_unemitted_parent": counts["parent_not_emitted"],
        "coverage": cov,
        "errors": errors,
        "warnings": warnings,
    }


def validate_corpus(chunks: Sequence[Chunk]) -> List[str]:
    """Cross-source checks: ids must be unique across the whole output file."""
    errors = []
    first: Dict[str, int] = {}
    for i, c in enumerate(chunks):
        if c.doc_id in first:
            errors.append(f"doc_id {c.doc_id!r} appears more than once in the corpus (records {first[c.doc_id]} and {i})")
        first.setdefault(c.doc_id, i)
    return errors
