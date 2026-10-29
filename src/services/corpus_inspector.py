"""Corpus, PDF and Chunk inspection service for LuatCheck RAG Inspector.

Provides clean overview, chunk extraction, and secure PDF streaming for both:
- Labour corpus (labour_vi_v1)
- HCMUT academic corpus (hcmut_academic_v1)
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def normalize_corpus_name(name: Optional[str]) -> str:
    """Normalize input corpus query parameter to canonical id ('labour' or 'hcmut')."""
    raw = (name or "").strip().lower()
    if not raw or any(k in raw for k in ("labour", "labor", "bll2019", "bll")):
        return "labour"
    if any(k in raw for k in ("hcmut", "academic")):
        return "hcmut"
    raise ValueError(f"Bộ văn bản '{name}' không tồn tại. Các bộ hỗ trợ: 'labour', 'hcmut'.")


def detect_clauses_and_points(text: str, title: str = "") -> Tuple[int, int]:
    """Detect number of statutory clauses (Khoản) and points (Điểm) in Vietnamese legal chunk."""
    body = text or ""
    if title and body.startswith(title):
        body = body[len(title) :]
    else:
        body = re.sub(r"^(?:Điều\s+\d+[a-zđ]?|Phụ\s+lục\s+\d+)[^\d]*\b", "", body, flags=re.IGNORECASE)

    # Clauses: e.g. " 1. ", " 2. ", "Khoản 1"
    clauses = re.findall(r"(?:^|\s)(?:Khoản\s+\d+|[1-9]\d*)\.\s+[A-ZÀ-Ỹ“\"]", body)
    # Points: e.g. " a) ", " b) ", "Điểm a"
    points = re.findall(r"(?:^|\s)(?:Điểm\s+[a-zđ]|[a-zđ]\))\s+[a-zà-ỹA-ZÀ-Ỹ“\"]", body)
    return len(clauses), len(points)


class CorpusInspector:
    """In-memory loaded and cached corpus inspector for legal documents and chunks."""

    def __init__(self, root_dir: Optional[Path] = None):
        self.root_dir = (root_dir or REPO_ROOT).resolve()
        self._data_cache: Dict[str, Dict[str, Any]] = {}
        self._load_corpora()

    def _resolve_repo_path(self, rel_path: str) -> Optional[Path]:
        try:
            target = (self.root_dir / rel_path).resolve()
            if target.is_relative_to(self.root_dir) and target.is_file():
                return target
        except Exception:
            pass
        return None

    def _load_corpora(self) -> None:
        self._data_cache["labour"] = self._load_labour_corpus()
        self._data_cache["hcmut"] = self._load_hcmut_corpus()

    def _load_labour_corpus(self) -> Dict[str, Any]:
        corpus_path = self.root_dir / "data/corpus/labour_vi_v1.json"
        manifest_path = self.root_dir / "data/corpus/labour_vi_v1.manifest.json"

        # Fallback if primary is missing
        if not corpus_path.is_file():
            corpus_path = self.root_dir / "data/corpus/labor_code_2019_official.json"
        if not manifest_path.is_file():
            manifest_path = self.root_dir / "data/corpus/labor_code_2019_ingested.manifest.json"

        manifest_data: Dict[str, Any] = {}
        if manifest_path.is_file():
            try:
                manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
            except Exception as e:
                logger.warning("Failed to load labour manifest: %s", e)

        raw_chunks: List[Dict[str, Any]] = []
        if corpus_path.is_file():
            try:
                raw_chunks = json.loads(corpus_path.read_text(encoding="utf-8"))
            except Exception as e:
                logger.warning("Failed to load labour corpus: %s", e)

        # Build document definitions from manifest sources
        docs_map: Dict[str, Dict[str, Any]] = {}
        pdf_whitelist: Dict[str, Path] = {}

        manifest_sources = manifest_data.get("sources", [])
        if isinstance(manifest_sources, list):
            for src in manifest_sources:
                doc_code = src.get("doc_code") or ""
                rel_pdf = src.get("path") or ""
                abs_pdf = self._resolve_repo_path(rel_pdf)
                doc_title = src.get("source_name") or doc_code
                pages = int(src.get("pages") or 0)
                file_bytes = int(src.get("bytes") or (abs_pdf.stat().st_size if abs_pdf else 0))
                sha256 = src.get("sha256") or ""
                pdf_filename = Path(rel_pdf).name if rel_pdf else ""
                document_number = src.get("document_number") or ""
                issued_date = src.get("issued_date") or ""
                effective_date = src.get("effective_date") or ""
                extraction_info = src.get("extraction") or ""

                if doc_code:
                    docs_map[doc_code] = {
                        "doc_code": doc_code,
                        "doc_title": doc_title,
                        "pdf_filename": pdf_filename,
                        "pdf_available": abs_pdf is not None,
                        "pdf_url": f"/api/corpus/pdf/labour/{doc_code}",
                        "pages": pages,
                        "bytes": file_bytes,
                        "sha256": sha256,
                        "document_number": document_number,
                        "issued_date": issued_date,
                        "effective_date": effective_date,
                        "extraction": extraction_info,
                        "chunk_count": 0,
                        "chapters": [],
                        "_abs_path": abs_pdf,
                    }
                    if abs_pdf:
                        pdf_whitelist[doc_code] = abs_pdf
                        if doc_code == "BLLD2019":
                            pdf_whitelist["BLL2019"] = abs_pdf

        # Process and normalize chunks
        processed_chunks: List[Dict[str, Any]] = []
        doc_chapters: Dict[str, List[str]] = {}

        for item in raw_chunks:
            article_id = item.get("doc_id") or ""
            doc_code = item.get("doc_code") or ""
            if not doc_code and "_" in article_id:
                doc_code = article_id.split("_")[0]
            if doc_code == "BLL2019" and "BLLD2019" in docs_map:
                doc_code = "BLLD2019"

            title = item.get("title") or article_id
            content = item.get("content") or ""
            section_path = item.get("section_path") or []
            chapter = section_path[0] if (isinstance(section_path, list) and section_path) else None

            doc_meta = docs_map.get(doc_code, {})
            doc_title = doc_meta.get("doc_title") or item.get("source_name") or doc_code

            if doc_code in docs_map:
                docs_map[doc_code]["chunk_count"] += 1
                if chapter and chapter not in doc_chapters.setdefault(doc_code, []):
                    doc_chapters[doc_code].append(chapter)

            clauses, points = detect_clauses_and_points(content, title)
            source_pages = item.get("source_pages") or []
            processed_chunks.append({
                "article_id": article_id,
                "title": title,
                "chapter": chapter,
                "doc_code": doc_code,
                "doc_title": doc_title,
                "text": content,
                "char_count": len(content),
                "word_count": len(content.split()),
                "clause_count": clauses,
                "point_count": points,
                "pdf_url": f"/api/corpus/pdf/labour/{doc_code}",
                "source_pages": source_pages,
                "char_start": item.get("char_start"),
                "char_end": item.get("char_end"),
                "document_number": item.get("document_number") or doc_meta.get("document_number"),
                "issued_date": item.get("issued_date") or doc_meta.get("issued_date"),
                "effective_date": item.get("effective_date") or doc_meta.get("effective_date"),
                "extraction": item.get("extraction") or doc_meta.get("extraction"),
            })

        for doc_code, chapters in doc_chapters.items():
            if doc_code in docs_map:
                docs_map[doc_code]["chapters"] = chapters

        # Alias support for BLL2019
        if "BLLD2019" in docs_map and "BLL2019" not in docs_map:
            docs_map["BLL2019"] = docs_map["BLLD2019"]

        return {
            "corpus": "labour",
            "collection_id": "labour_vi_v1",
            "title": "Bộ Pháp luật Lao động Việt Nam",
            "chunking_granularity": "Theo từng Điều (Article-level)",
            "id_template": "{doc_code}_Dieu_{num_ascii}",
            "manifest_summary": manifest_data.get("totals", {}),
            "documents": [d for k, d in docs_map.items() if k != "BLL2019"],
            "documents_map": docs_map,
            "chunks": processed_chunks,
            "pdf_whitelist": pdf_whitelist,
        }

    def _load_hcmut_corpus(self) -> Dict[str, Any]:
        corpus_path = self.root_dir / "data/corpus/hcmut_academic_v1.json"
        manifest_path = self.root_dir / "data/corpus/hcmut_academic_ingested.manifest.json"
        source_manifest_path = self.root_dir / "docs/materials/hcmut-sources/manifest.json"

        manifest_data: Dict[str, Any] = {}
        if manifest_path.is_file():
            try:
                manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
            except Exception as e:
                logger.warning("Failed to load hcmut manifest: %s", e)

        source_manifest: Dict[str, Any] = {}
        if source_manifest_path.is_file():
            try:
                source_manifest = json.loads(source_manifest_path.read_text(encoding="utf-8"))
            except Exception as e:
                logger.warning("Failed to load hcmut source manifest: %s", e)

        raw_chunks: List[Dict[str, Any]] = []
        if corpus_path.is_file():
            try:
                raw_chunks = json.loads(corpus_path.read_text(encoding="utf-8"))
            except Exception as e:
                logger.warning("Failed to load hcmut corpus: %s", e)

        docs_map: Dict[str, Dict[str, Any]] = {}
        pdf_whitelist: Dict[str, Path] = {}

        # Build metadata lookup from source manifest
        hcmut_source_doc_meta: Dict[str, Dict[str, Any]] = {}
        for d in source_manifest.get("documents", []):
            code = d.get("doc_code")
            if code:
                hcmut_source_doc_meta[code] = d

        # Load from manifest sources
        sources = manifest_data.get("sources", [])
        if isinstance(sources, list):
            for src in sources:
                doc_code = src.get("doc_code") or ""
                rel_pdf = src.get("path") or ""
                abs_pdf = self._resolve_repo_path(rel_pdf)
                doc_title = src.get("source_name") or doc_code
                pages = int(src.get("pages") or 0)
                file_bytes = int(src.get("bytes") or (abs_pdf.stat().st_size if abs_pdf else 0))
                sha256 = src.get("sha256") or ""
                pdf_filename = Path(rel_pdf).name if rel_pdf else ""

                extra = hcmut_source_doc_meta.get(doc_code, {})
                document_number = extra.get("document_number") or src.get("document_number") or ""
                issued_date = extra.get("issued_date") or src.get("issued_date") or ""
                effective_date = extra.get("effective_date") or src.get("effective_date") or ""
                extraction_info = extra.get("verification_notes") or src.get("extraction") or ""

                if doc_code:
                    docs_map[doc_code] = {
                        "doc_code": doc_code,
                        "doc_title": doc_title,
                        "pdf_filename": pdf_filename,
                        "pdf_available": abs_pdf is not None,
                        "pdf_url": f"/api/corpus/pdf/hcmut/{doc_code}",
                        "pages": pages,
                        "bytes": file_bytes,
                        "sha256": sha256,
                        "document_number": document_number,
                        "issued_date": issued_date,
                        "effective_date": effective_date,
                        "extraction": extraction_info,
                        "chunk_count": 0,
                        "chapters": [],
                        "_abs_path": abs_pdf,
                    }
                    if abs_pdf:
                        pdf_whitelist[doc_code] = abs_pdf

        # Process and normalize HCMUT chunks
        processed_chunks: List[Dict[str, Any]] = []
        doc_chapters: Dict[str, List[str]] = {}
        active_chapter_by_doc: Dict[str, str] = {}

        for item in raw_chunks:
            article_id = item.get("doc_id") or ""
            # e.g. HCMUT_HVDT1260_Dieu_1
            parts = article_id.split("_")
            doc_code = item.get("doc_code") or ""
            if not doc_code and len(parts) >= 2:
                doc_code = parts[1]

            title = item.get("title") or article_id
            content = item.get("content") or ""

            # Detect chapter / regulation section
            chapter = active_chapter_by_doc.get(doc_code, "Điều khoản chung")
            m_chap = re.search(r"(Chương\s+[IVXLCDM0-9]+[^\.\n\:]*)", content)
            if m_chap:
                chapter = m_chap.group(1).strip()
                active_chapter_by_doc[doc_code] = chapter
            elif "PHỤ LỤC" in title.upper():
                chapter = title.strip()
                active_chapter_by_doc[doc_code] = chapter

            doc_meta = docs_map.get(doc_code, {})
            doc_title = doc_meta.get("doc_title") or item.get("source_name") or doc_code

            if doc_code in docs_map:
                docs_map[doc_code]["chunk_count"] += 1
                if chapter and chapter not in doc_chapters.setdefault(doc_code, []):
                    doc_chapters[doc_code].append(chapter)

            clauses, points = detect_clauses_and_points(content, title)
            source_pages = item.get("source_pages") or []
            processed_chunks.append({
                "article_id": article_id,
                "title": title,
                "chapter": chapter,
                "doc_code": doc_code,
                "doc_title": doc_title,
                "text": content,
                "char_count": len(content),
                "word_count": len(content.split()),
                "clause_count": clauses,
                "point_count": points,
                "pdf_url": f"/api/corpus/pdf/hcmut/{doc_code}",
                "source_pages": source_pages,
                "char_start": item.get("char_start"),
                "char_end": item.get("char_end"),
                "document_number": item.get("document_number") or doc_meta.get("document_number"),
                "issued_date": item.get("issued_date") or doc_meta.get("issued_date"),
                "effective_date": item.get("effective_date") or doc_meta.get("effective_date"),
                "extraction": item.get("extraction") or item.get("metadata_verification") or doc_meta.get("extraction"),
            })

        for doc_code, chapters in doc_chapters.items():
            if doc_code in docs_map:
                docs_map[doc_code]["chapters"] = chapters

        return {
            "corpus": "hcmut",
            "collection_id": "hcmut_academic",
            "title": "Quy chế & Quy định Học vụ Trường ĐH Bách Khoa - ĐHQG-HCM",
            "chunking_granularity": "Theo từng Điều & Khoản sửa đổi (Article & Amendment Clause level)",
            "id_template": "HCMUT_{doc_code}_{section_id}",
            "manifest_summary": manifest_data.get("totals", {}),
            "documents": list(docs_map.values()),
            "documents_map": docs_map,
            "chunks": processed_chunks,
            "pdf_whitelist": pdf_whitelist,
        }

    def get_overview(self, corpus_id: str) -> Dict[str, Any]:
        cid = normalize_corpus_name(corpus_id)
        data = self._data_cache.get(cid)
        if not data:
            raise ValueError(f"Corpus '{corpus_id}' is not configured.")

        docs_clean = []
        for d in data["documents"]:
            doc_dict = {k: v for k, v in d.items() if not k.startswith("_")}
            docs_clean.append(doc_dict)

        total_chars = sum(c["char_count"] for c in data["chunks"])

        return {
            "corpus": cid,
            "collection_id": data["collection_id"],
            "title": data["title"],
            "chunking_granularity": data["chunking_granularity"],
            "id_template": data["id_template"],
            "total_documents": len(docs_clean),
            "total_chunks": len(data["chunks"]),
            "total_characters": total_chars,
            "manifest_summary": data["manifest_summary"],
            "documents": docs_clean,
        }

    def get_chunks(
        self,
        corpus_id: str,
        doc_code: Optional[str] = None,
        q: Optional[str] = None,
        chapter: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        cid = normalize_corpus_name(corpus_id)
        data = self._data_cache.get(cid)
        if not data:
            raise ValueError(f"Corpus '{corpus_id}' is not configured.")

        chunks = data["chunks"]

        # Filter by doc_code
        if doc_code:
            target_code = doc_code.strip()
            if cid == "labour" and target_code == "BLL2019":
                target_code = "BLLD2019"
            chunks = [c for c in chunks if c["doc_code"].lower() == target_code.lower()]

        # Filter by chapter
        if chapter and chapter.strip():
            chap_filter = chapter.strip().lower()
            chunks = [c for c in chunks if c.get("chapter") and chap_filter in c["chapter"].lower()]

        # Filter by search query q
        if q and q.strip():
            query_str = q.strip().lower()
            chunks = [
                c
                for c in chunks
                if query_str in c["article_id"].lower()
                or query_str in c["title"].lower()
                or query_str in c["text"].lower()
                or (c.get("chapter") and query_str in c["chapter"].lower())
            ]

        total = len(chunks)
        limit = max(1, min(limit, 500))
        offset = max(0, offset)
        items = chunks[offset : offset + limit]

        return {
            "corpus": cid,
            "total": total,
            "limit": limit,
            "offset": offset,
            "items": items,
        }

    def resolve_pdf(self, corpus_id: str, doc_code: str) -> Optional[Path]:
        """Strict whitelist resolution for PDF file path."""
        cid = normalize_corpus_name(corpus_id)
        data = self._data_cache.get(cid)
        if not data:
            return None

        clean_code = (doc_code or "").strip()
        if cid == "labour" and clean_code == "BLL2019":
            clean_code = "BLLD2019"

        target_path = data["pdf_whitelist"].get(clean_code)
        if target_path and target_path.is_file():
            # Security verification against traversal
            resolved = target_path.resolve()
            if resolved.is_relative_to(self.root_dir):
                return resolved

        return None


# Global singleton instance
_GLOBAL_INSPECTOR: Optional[CorpusInspector] = None


def get_corpus_inspector() -> CorpusInspector:
    global _GLOBAL_INSPECTOR
    if _GLOBAL_INSPECTOR is None:
        _GLOBAL_INSPECTOR = CorpusInspector()
    return _GLOBAL_INSPECTOR
