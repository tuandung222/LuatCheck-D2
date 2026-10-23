"""
Universal Document and Citation Schemas for Multi-Domain Knowledge Representation.

Supports arbitrary domain corpora (Legal, Medical, Financial, Enterprise IT SOPs).
"""
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class UniversalDocument(BaseModel):
    """
    Universal knowledge document chunk representation across any industry domain.
    """
    doc_id: str = Field(description="Unique identifier for the document or section (e.g. 'Dieu_25', 'SOP_SEC_01')")
    collection_id: str = Field(default="default", description="Collection or dataset ID (e.g. 'labor_code_2019', 'it_sop')")
    source_name: str = Field(default="", description="Name of the source document or manual")
    section_title: str = Field(default="", description="Title of the section, article, or chapter")
    content: str = Field(description="Verbatim text content of the document chunk")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary domain metadata (tags, author, etc.)")

    @property
    def article_id(self) -> str:
        return self.doc_id

    @property
    def law_name(self) -> str:
        return self.source_name

    @property
    def law_id(self) -> str:
        return self.collection_id

    @property
    def title(self) -> str:
        return self.section_title

    def to_legacy_dict(self) -> Dict[str, Any]:
        return {
            "article_id": self.doc_id,
            "law_id": self.collection_id,
            "law_name": self.source_name,
            "title": self.section_title,
            "content": self.content,
            **self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UniversalDocument":
        doc_id = str(data.get("doc_id") or data.get("article_id") or data.get("id") or "")
        collection_id = str(data.get("collection_id") or data.get("law_id") or "default")
        source_name = str(data.get("source_name") or data.get("law_name") or "")
        section_title = str(data.get("section_title") or data.get("title") or "")
        content = str(data.get("content") or data.get("text") or "")
        meta = {
            k: v for k, v in data.items()
            if k not in {
                "doc_id", "article_id", "id", "collection_id", "law_id",
                "source_name", "law_name", "section_title", "title", "content", "text"
            }
        }
        return cls(
            doc_id=doc_id,
            collection_id=collection_id,
            source_name=source_name,
            section_title=section_title,
            content=content,
            metadata=meta
        )


class UniversalCitation(BaseModel):
    """
    Universal attribution citation linking claim statements to source documents.
    """
    doc_id: str = Field(description="Referenced document identifier")
    source_name: str = Field(default="", description="Source publication or statute title")
    exact_quote: Optional[str] = Field(default=None, description="Direct excerpt supporting statement")

    @property
    def article_id(self) -> str:
        return self.doc_id

    @property
    def law_name(self) -> str:
        return self.source_name
