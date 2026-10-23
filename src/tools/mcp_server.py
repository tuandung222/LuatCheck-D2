"""
Local SLM CPU - MCP Server (Model Context Protocol).
Provides standardized tools via the MCP SDK v2 MCPServer API.
"""
from typing import Dict, Any
from mcp.server.mcpserver import MCPServer
from src.config.app_config import load_config
from src.domains import load_profile
from src.tools.legal_tools import LegalToolRegistry

# The application loop calls its registry directly; this is a separate entry point.
# Model-facing tool names and descriptions come from the configured domain profile
# (labour_vi_2019 by default: search_law / get_article).
config = load_config()
profile = load_profile(config.domain.profile)
mcp = MCPServer("luatcheck-local-tools")
registry = LegalToolRegistry(corpus_path=config.retrieval.corpus_path, profile=profile)


def search_documents(query: str, top_k: int = 5) -> Dict[str, Any]:
    return registry.search_knowledge(query=query, top_k=top_k)


def read_document(article_id: str) -> Dict[str, Any]:
    return registry.get_document(article_id)


search_documents.__name__ = profile.tools.search.name
read_document.__name__ = profile.tools.read.name
mcp.tool(name=profile.tools.search.name, description=profile.tools.search.description)(search_documents)
mcp.tool(name=profile.tools.read.name, description=profile.tools.read.description)(read_document)
# Backward-compatible module-level names for the labour tools.
search_law = search_documents
get_article = read_document


@mcp.tool()
def save_case(case_id: str, summary: str, client_name: str = "Anonymous") -> Dict[str, Any]:
    """
    Blocked write interface: model callers cannot self-attest verification.
    """
    return {"status": "blocked_unverified_write", "message": "MCP callers cannot self-attest verification. Only the verified agent memory path persists consultations."}


@mcp.tool()
def send_summary(
    recipient: str,
    content: str,
    idempotency_key: str
) -> Dict[str, Any]:
    """
    Proposes a local-outbox action. This model-facing tool cannot approve or execute it.
    Approval and execution are available only through the trusted host UI.
    """
    return registry.send_summary(
        recipient=recipient,
        content=content,
        idempotency_key=idempotency_key,
        user_confirmed=False
    )


if __name__ == "__main__":
    # Launch stdio transport adhering to the MCP standard
    mcp.run(transport="stdio")
