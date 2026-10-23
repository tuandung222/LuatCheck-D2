"""Text normalisation with page/offset mapping.

Only formatting is normalised: Unicode NFC, exotic spaces and zero-width characters, runs of whitespace inside a
line, blank lines, repeated running headers/footers and bare page numbers, and (optionally) hyphenated line
breaks. Words are never reordered, dropped or corrected. Line breaks are kept (one physical line per line of
the source) so structural rules can use them; chunk content may later be whitespace-collapsed, but the
normalised text itself remains the reference every chunk is verified against.

Running-header detection: a line is a repeated header/footer when its *shape* (digits masked, whitespace
collapsed) occurs inside the first/last `edge_lines` lines of at least `min_page_fraction` of the pages (and at
least `min_pages` pages). Every removal is reported (shape, count, sample) so it can be audited.
"""
from __future__ import annotations

import math
import re
import unicodedata
from bisect import bisect_right
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .errors import ConfigError
from .loaders import LoadedDocument

_ZERO_WIDTH = dict.fromkeys(map(ord, "\u200b\u200c\u200d\u2060\ufeff"), None)
_SPACE_CHARS = {ord(c): " " for c in "\u00a0\u1680\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a\u202f\u205f\u3000\t\f\v"}
_PAGE_NUMBER = re.compile(r"^(?:(?:trang|page)\s+)?\d{1,4}(?:\s*(?:/|of|trên)\s*\d{1,4})?$", re.I)


@dataclass
class NormalizeConfig:
    nfc: bool = True
    remove_repeated_edges: bool = True
    edge_lines: int = 3
    min_page_fraction: float = 0.3
    min_pages: int = 3
    strip_page_numbers: bool = True
    remove_line_patterns: List[str] = field(default_factory=list)  # regexes (re.search) for lines to drop everywhere
    join_hyphenated: bool = False  # ASCII "-" at end of line + lowercase start of next; off by default (ambiguous)
    blank_lines: Optional[str] = None  # "drop" | "single" | "keep"; None = drop for paginated, single otherwise

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "NormalizeConfig":
        data = dict(data or {})
        unknown = set(data) - set(cls.__dataclass_fields__)
        if unknown:
            raise ConfigError(f"unknown normalize option(s): {sorted(unknown)}")
        cfg = cls(**data)
        if cfg.blank_lines not in (None, "drop", "single", "keep"):
            raise ConfigError("normalize.blank_lines must be drop, single or keep")
        for pat in cfg.remove_line_patterns:
            try:
                re.compile(pat)
            except re.error as exc:
                raise ConfigError(f"invalid normalize.remove_line_patterns entry {pat!r}: {exc}") from exc
        return cfg


@dataclass
class NormalizedDocument:
    text: str
    page_spans: List[Tuple[Optional[int], int, int]]  # (page number, start, end) in `text`, end exclusive
    removed: List[Dict[str, Any]]  # audit of every removed running header/footer/page number (grouped)
    warnings: List[str]

    def pages_for(self, start: int, end: int) -> List[int]:
        """Page numbers whose span intersects [start, end). Empty for unpaginated formats."""
        pages: List[int] = []
        if not self.page_spans or self.page_spans[0][0] is None:
            return pages
        starts = [s for _, s, _ in self.page_spans]
        i = max(0, bisect_right(starts, start) - 1)
        while i < len(self.page_spans):
            number, s, e = self.page_spans[i]
            if s >= end:
                break
            if e > start and s < end:
                pages.append(number)
            i += 1
        return pages


def _clean_line(line: str, cfg: NormalizeConfig) -> str:
    if cfg.nfc:
        line = unicodedata.normalize("NFC", line)
    soft = line.endswith("\u00ad")
    line = line.replace("\u00ad", "").translate(_ZERO_WIDTH).translate(_SPACE_CHARS)
    line = " ".join(line.split())
    return line + ("\u00ad" if soft else "")  # keep a marker for an end-of-line soft hyphen; resolved in _join


def _shape(line: str) -> str:
    return re.sub(r"\d+", "#", " ".join(line.split()))


def normalize(doc: LoadedDocument, cfg: Optional[NormalizeConfig] = None) -> NormalizedDocument:
    cfg = cfg or NormalizeConfig()
    paginated = any(p.number is not None for p in doc.pages)
    blank_policy = cfg.blank_lines or ("drop" if paginated else "single")
    line_patterns = [re.compile(p) for p in cfg.remove_line_patterns]
    removed: Counter = Counter()
    samples: Dict[str, str] = {}
    reasons: Dict[str, str] = {}

    def record_removal(reason: str, line: str):
        key = f"{reason}\x00{_shape(line)}"
        removed[key] += 1
        samples.setdefault(key, line)
        reasons[key] = reason

    # 1. per-page cleaned lines (keep blank lines for now)
    page_lines: List[List[str]] = []
    for page in doc.pages:
        text = page.text.replace("\r\n", "\n").replace("\r", "\n")
        page_lines.append([_clean_line(ln, cfg) for ln in text.split("\n")])

    # 2. user-supplied line patterns
    if line_patterns:
        for i, lines in enumerate(page_lines):
            kept = []
            for line in lines:
                if line and any(p.search(line) for p in line_patterns):
                    record_removal("pattern", line)
                else:
                    kept.append(line)
            page_lines[i] = kept

    # 3. repeated edge lines across pages
    if cfg.remove_repeated_edges and paginated:
        non_empty_pages = [lines for lines in page_lines if any(lines)]
        threshold = max(cfg.min_pages, math.ceil(cfg.min_page_fraction * len(non_empty_pages)))
        if len(non_empty_pages) >= cfg.min_pages:
            seen_on_pages: Dict[str, int] = defaultdict(int)
            for lines in non_empty_pages:
                idx = [i for i, ln in enumerate(lines) if ln]
                edge = idx[:cfg.edge_lines] + idx[-cfg.edge_lines:]
                for shape in {_shape(lines[i]) for i in set(edge)}:
                    seen_on_pages[shape] += 1
            repeated = {s for s, n in seen_on_pages.items() if n >= threshold}
            for p_i, lines in enumerate(page_lines):
                idx = [i for i, ln in enumerate(lines) if ln]
                edge = set(idx[:cfg.edge_lines] + idx[-cfg.edge_lines:])
                kept = []
                for i, line in enumerate(lines):
                    if i in edge and line and _shape(line) in repeated:
                        record_removal("repeated_edge_line", line)
                    else:
                        kept.append(line)
                page_lines[p_i] = kept

    # 4. bare page numbers at the page edges
    if cfg.strip_page_numbers and paginated:
        for p_i, lines in enumerate(page_lines):
            idx = [i for i, ln in enumerate(lines) if ln]
            if not idx:
                continue
            for i in {idx[0], idx[-1]}:
                if _PAGE_NUMBER.match(lines[i]):
                    record_removal("page_number", lines[i])
                    lines[i] = ""

    # 5. hyphenation joins (within a page only) and blank-line policy
    for p_i, lines in enumerate(page_lines):
        out: List[str] = []
        for line in lines:
            if out and out[-1].endswith("\u00ad") and line:
                out[-1] = out[-1][:-1] + line  # soft hyphen at line end: unambiguous join, no space
                continue
            if (cfg.join_hyphenated and out and line and re.search(r"[^\W\d_]-$", out[-1])
                    and line[0].isalpha() and line[0].islower()):
                out[-1] = out[-1][:-1] + line
                continue
            out.append(line)
        out = [ln[:-1] if ln.endswith("\u00ad") else ln for ln in out]
        if blank_policy == "drop":
            out = [ln for ln in out if ln]
        elif blank_policy == "single":
            squeezed: List[str] = []
            for ln in out:
                if ln or (squeezed and squeezed[-1]):
                    squeezed.append(ln)
            while squeezed and not squeezed[-1]:
                squeezed.pop()
            out = squeezed
        else:
            while out and not out[-1]:
                out.pop()
            while out and not out[0]:
                out.pop(0)
        page_lines[p_i] = out

    # 6. assemble text + page spans
    parts: List[str] = []
    spans: List[Tuple[Optional[int], int, int]] = []
    pos = 0
    for page, lines in zip(doc.pages, page_lines):
        body = "\n".join(lines)
        if not body.strip():
            continue
        if parts:
            pos += 1  # the "\n" separator between pages
        spans.append((page.number, pos, pos + len(body)))
        parts.append(body)
        pos += len(body)
    text = "\n".join(parts)

    audit = [{"reason": reasons[k], "shape": k.split("\x00", 1)[1], "count": n, "sample": samples[k]}
             for k, n in sorted(removed.items(), key=lambda kv: (-kv[1], kv[0]))]
    return NormalizedDocument(text, spans, audit, list(doc.warnings))
