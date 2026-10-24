"""Citation objects built from model output or stored answers, with the domain profile's default source name."""
from typing import Any, Dict, List

from pydantic import ValidationError

from src.agent.state import Citation
from src.domains import DomainProfile


def build_citation(profile: DomainProfile, data: Dict[str, Any]) -> Citation:
    """A missing source name defaults to the profile's, not to a fixed statute."""
    return Citation(**{"law_name": profile.source_name, **data})


def parse_model_citations(profile: DomainProfile, raw: Any) -> List[Citation]:
    """Citations of a model `answer` action. Dicts with a usable `article_id` and non-empty strings are kept;
    anything else is skipped (the L1 verifier then rejects an answer left without citations)."""
    if not isinstance(raw, list):
        return []
    citations: List[Citation] = []
    for item in raw:
        if isinstance(item, dict):
            try:
                citations.append(build_citation(profile, item))
            except (ValidationError, TypeError):
                article_id = str(item.get("article_id") or "")
                if article_id:
                    citations.append(Citation(article_id=article_id, law_name=profile.source_name))
        elif isinstance(item, str) and item.strip():
            citations.append(Citation(article_id=item.strip(), law_name=profile.source_name))
    return citations


def dump_citations(citations: List[Citation]) -> List[Dict[str, Any]]:
    return [c.model_dump() for c in citations]
