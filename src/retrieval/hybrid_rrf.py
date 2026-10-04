"""
Hybrid Retrieval with Reciprocal Rank Fusion (RRF).

Delegates implementation to the domain-agnostic HybridDomainRetriever.
"""
from src.retrieval.hybrid_domain import HybridDomainRetriever

HybridLegalRetriever = HybridDomainRetriever

__all__ = ["HybridLegalRetriever", "HybridDomainRetriever"]
