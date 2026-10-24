"""
Legal Tool Registry.

Delegates implementation to the domain-agnostic DomainKnowledgeRegistry.
"""
from src.tools.domain_tools import DomainKnowledgeRegistry

LegalToolRegistry = DomainKnowledgeRegistry

__all__ = ["LegalToolRegistry", "DomainKnowledgeRegistry"]
