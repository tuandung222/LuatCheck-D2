#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build data/corpus/hcmut_academic_v1.json from the downloaded HCMUT PDFs.

Inputs (all inside this folder):
  manifest.json      one entry per document: metadata, source URL, retrieval time (UTC),
                     and the file name. Computed fields (sha256, pages, sections,
                     text-layer status, notes) are written back into this file.
  <FILE>.pdf         the downloaded PDFs listed in manifest.json.

Outputs:
  data/corpus/hcmut_academic_v1.json   corpus records (one per section)
  extracted/<CODE>.raw.txt             pypdf text per page, before any cleaning
  extracted/<CODE>.clean.txt           text after removing page numbers and repeated
                                       running headers/footers (used for the content check)

Run from the repository root:
  .venv/bin/python -I docs/materials/hcmut-sources/extract_hcmut_corpus.py
Verify (recompute sha256, check each record against the extracted text, check ids):
  .venv/bin/python -I docs/materials/hcmut-sources/extract_hcmut_corpus.py --check

Only whitespace and Unicode (NFC) normalisation is applied to the text, plus removal of
bare page numbers and running headers/footers that repeat at the page edges.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import unicodedata
from collections import Counter, OrderedDict
from pathlib import Path

from pypdf import PdfReader

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent.parent
MANIFEST = HERE / "manifest.json"
EXTRACT_DIR = HERE / "extracted"
OUT_PATH = REPO / "data" / "corpus" / "hcmut_academic_v1.json"
COLLECTION_ID = "hcmut_academic"
CLAUSE_SPLIT_CHARS = 6000  # sections longer than this are split at numbered clauses
MAX_PAGES = 25  # corpus limit: every included document must be at most this many pages
TEXT_PAGE_MIN_CHARS = 50

ART_RE = re.compile(unicodedata.normalize("NFC", r"^Điều\s+(\d+[a-z]?)\s*\.\s*(.*)$"))
APP_RE = re.compile(unicodedata.normalize("NFC", r"^(?:PHỤ LỤC|Phụ lục)\s+(\d+)\s*(?:[:.]|$)"))
CLAUSE_RE = re.compile(r'^["“]?(\d{1,2})\.(\d{1,2})\s+\S')


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def norm_line(s: str) -> str:
    s = unicodedata.normalize("NFC", s).replace(" ", " ").replace("​", "")
    return re.sub(r"[ \t\r\f\v]+", " ", s).strip()


def load_pages(path: Path):
    """Return list of (page_no, [cleaned-whitespace lines]) and the raw page texts."""
    reader = PdfReader(str(path))
    pages, raw_pages = [], []
    for i, pg in enumerate(reader.pages, 1):
        raw = pg.extract_text() or ""
        raw_pages.append((i, raw))
        lines = [norm_line(x) for x in raw.split("\n")]
        pages.append((i, [x for x in lines if x]))
    return pages, raw_pages


def clean_pages(pages):
    """Drop bare page numbers and running headers/footers repeated on >=3 pages (edge lines)."""
    edge_counts: Counter = Counter()
    for _, lines in pages:
        edges = set(lines[:3] + lines[-3:])
        for line in edges:
            if len(line) <= 120 and not ART_RE.match(line) and re.search(r"[^\W\d_]{3,}", line):
                edge_counts[line] += 1
    repeated = {line for line, c in edge_counts.items() if c >= 3}
    removed: Counter = Counter()
    out = []  # (page_no, line)
    for pno, lines in pages:
        n = len(lines)
        for idx, line in enumerate(lines):
            at_edge = idx < 3 or idx >= n - 3
            if at_edge and line in repeated:
                removed[line] += 1
                continue
            if at_edge and re.fullmatch(r"-?\s*\d{1,3}\s*-?", line):
                removed["<bare page number>"] += 1
                continue
            out.append((pno, line))
    return out, removed


def segment(lines):
    """Split cleaned lines [(page, text)] into section dicts keyed by section id."""
    heads = []  # (line_index, kind, key, heading_text)
    seen_ge2 = False
    annex_reset = None
    for idx, (_, line) in enumerate(lines):
        m = ART_RE.match(line)
        if m:
            num = m.group(1)
            n_int = int(re.match(r"\d+", num).group())
            if n_int == 1 and seen_ge2 and annex_reset is None:
                annex_reset = idx  # numbering restarts: an attached regulation begins here
            if n_int >= 2:
                seen_ge2 = True
            heads.append((idx, "art", num, line))
            continue
        m = APP_RE.match(line)
        if m:
            heads.append((idx, "app", m.group(1), line))

    def art_id(num: str, idx: int) -> str:
        if annex_reset is not None and idx < annex_reset:
            return f"QD_Dieu_{num}"
        return f"Dieu_{num}"

    raw_sections = []  # (base_id, heading, span_lines)
    for k, (idx, kind, key, head_line) in enumerate(heads):
        end = heads[k + 1][0] if k + 1 < len(heads) else len(lines)
        base = art_id(key, idx) if kind == "art" else f"PhuLuc_{key}"
        raw_sections.append((base, head_line, lines[idx:end]))

    sections = []
    for base, head_line, span in raw_sections:
        # Split oversized sections at numbered clauses (e.g. quoted clauses 3.1, 5.2 of an amended text).
        content_len = sum(len(t) + 1 for _, t in span)
        clause_starts = [i for i, (_, t) in enumerate(span) if i > 0 and CLAUSE_RE.match(t)]
        if content_len > CLAUSE_SPLIT_CHARS and len(clause_starts) >= 2:
            bounds = [0] + clause_starts + [len(span)]
            for j in range(len(bounds) - 1):
                piece = span[bounds[j]:bounds[j + 1]]
                if not piece:
                    continue
                if j == 0:
                    sid = base
                    title = head_line
                else:
                    m = CLAUSE_RE.match(piece[0][1])
                    sid = f"{base}_S{m.group(1)}_{m.group(2)}"
                    title = piece[0][1]
                sections.append((sid, title, piece))
        else:
            sections.append((base, head_line, span))

    # Make ids unique within the document.
    seen: Counter = Counter()
    final = []
    for sid, title, span in sections:
        seen[sid] += 1
        if seen[sid] > 1:
            sid = f"{sid}_{seen[sid]}"
        final.append((sid, title, span))
    return final, annex_reset is not None, [h[3] for h in heads]


def build_section_record(src, sid, title, span):
    content = "\n".join(t for _, t in span)
    pages = sorted({p for p, _ in span})
    return OrderedDict([
        ("doc_id", f"HCMUT_{src['doc_code']}_{sid}"),
        ("collection_id", COLLECTION_ID),
        ("source_name", f"{src['title']} — số {src['document_number']}"),
        ("title", title),
        ("content", content),
        ("source_url", src["source_url"]),
        ("source_sha256", src["sha256"]),
        ("source_pages", pages),
        ("retrieved_at", src["retrieved_at"]),
        ("document_number", src["document_number"]),
        ("issued_date", src["issued_date"]),
        ("metadata_verification", src["metadata_verification"]),
    ])


def process_all(manifest, write_extracts=True):
    records = []
    notes_all = {}
    for src in manifest["documents"]:
        path = HERE / src["file"]
        pages, raw_pages = load_pages(path)
        cleaned, removed = clean_pages(pages)
        sections, has_annex, head_lines = segment(cleaned)
        n_pages = len(pages)
        pages_with_text = sum(1 for _, lines in pages if sum(len(x) for x in lines) >= TEXT_PAGE_MIN_CHARS)
        clean_chars = sum(len(t) for _, t in cleaned)

        src["sha256"] = sha256_of(path)
        src["pages"] = n_pages
        src["text_layer_usable"] = pages_with_text / max(n_pages, 1) >= 0.8
        src["pages_with_text"] = pages_with_text
        src["chars_extracted"] = clean_chars
        src["sections"] = len(sections)
        src["section_ids"] = [sid for sid, _, _ in sections]
        src["extraction_notes"] = {
            "annex_numbering_reset": has_annex,
            "removed_lines": {k: v for k, v in removed.most_common(12)},
            "article_headings_found": len(head_lines),
        }

        if write_extracts:
            EXTRACT_DIR.mkdir(exist_ok=True)
            with (EXTRACT_DIR / f"{src['doc_code']}.raw.txt").open("w", encoding="utf-8") as fh:
                for pno, raw in raw_pages:
                    fh.write(f"\n<<<PAGE {pno}>>>\n{unicodedata.normalize('NFC', raw)}")
            with (EXTRACT_DIR / f"{src['doc_code']}.clean.txt").open("w", encoding="utf-8") as fh:
                last = None
                for pno, line in cleaned:
                    if pno != last:
                        fh.write(f"\n<<<PAGE {pno}>>>\n")
                        last = pno
                    fh.write(line + "\n")

        if src.get("included_in_corpus", True):
            if n_pages > MAX_PAGES:
                raise SystemExit(f"{src['doc_code']} has {n_pages} pages > {MAX_PAGES}; set included_in_corpus false")
            for sid, title, span in sections:
                records.append(build_section_record(src, sid, title, span))
        else:
            src["sections"] = 0
            src["section_ids"] = []
    return records


def check(manifest) -> int:
    failures = []
    recs = json.loads(OUT_PATH.read_text(encoding="utf-8"))
    ids = [r["doc_id"] for r in recs]
    if len(ids) != len(set(ids)):
        failures.append("duplicate doc_id")
    for src in manifest["documents"]:
        path = HERE / src["file"]
        digest = sha256_of(path)
        if digest != src["sha256"]:
            failures.append(f"sha256 mismatch {src['doc_code']}")
        if src.get("included_in_corpus", True) and src["pages"] > MAX_PAGES:
            failures.append(f"{src['doc_code']} exceeds {MAX_PAGES} pages")
        if not src.get("included_in_corpus", True) and any(r["doc_id"].startswith(f"HCMUT_{src['doc_code']}_") for r in recs):
            failures.append(f"excluded document has records {src['doc_code']}")
        clean_text = (EXTRACT_DIR / f"{src['doc_code']}.clean.txt").read_text(encoding="utf-8")
        clean_flat = re.sub(r"\s+", " ", re.sub(r"<<<PAGE \d+>>>", " ", clean_text))
        raw_text = (EXTRACT_DIR / f"{src['doc_code']}.raw.txt").read_text(encoding="utf-8")
        raw_flat = re.sub(r"\s+", " ", raw_text)
        for r in recs:
            if not r["doc_id"].startswith(f"HCMUT_{src['doc_code']}_"):
                continue
            if not r["content"].strip():
                failures.append(f"empty content {r['doc_id']}")
            flat = re.sub(r"\s+", " ", r["content"])
            if flat not in clean_flat:
                failures.append(f"content not in clean text {r['doc_id']}")
            for line in r["content"].split("\n"):
                if re.sub(r"\s+", " ", line).strip() and re.sub(r"\s+", " ", line).strip() not in raw_flat:
                    failures.append(f"line not in raw text {r['doc_id']}: {line[:60]}")
                    break
    for r in recs:
        if not r["source_pages"]:
            failures.append(f"no pages {r['doc_id']}")
    print(f"records={len(recs)} unique_ids={len(set(ids))}")
    for src in manifest["documents"]:
        digest = sha256_of(HERE / src["file"])
        print(f"{src['doc_code']}: sha256_ok={digest == src['sha256']} sections={src['sections']}")
    if failures:
        print("FAILURES:")
        for f in failures:
            print("  -", f)
        return 1
    print("all checks passed")
    return 0


def main(argv) -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if "--check" in argv:
        return check(manifest)
    for src in manifest["documents"]:
        src["sha256"] = sha256_of(HERE / src["file"])
    records = process_all(manifest)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    manifest["total_sections"] = len(records)
    manifest["included_documents"] = sum(1 for d in manifest["documents"] if d.get("included_in_corpus", True))
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for src in manifest["documents"]:
        print(f"{src['doc_code']}: pages={src['pages']} text_layer_usable={src['text_layer_usable']} "
              f"sections={src['sections']} chars={src['chars_extracted']}")
        print(f"   headings: {src['section_ids'][:6]}")
    print(f"total sections={len(records)} -> {OUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
