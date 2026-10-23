"""
Local SLM CPU - MCP Server (Model Context Protocol).
Provides standardized tools via the MCP SDK v2 MCPServer API.
"""
from typing import Dict, Any, Optional
from mcp.server.mcpserver import MCPServer
from src.tools.legal_tools import LegalToolRegistry

# The application loop calls its registry directly; this is a separate entry point.
mcp = MCPServer("luatcheck-local-tools")
registry = LegalToolRegistry()


@mcp.tool()
def search_law(query: str, top_k: int = 5) -> Dict[str, Any]:
    """
    Searches labor law articles by natural query or semantic keywords.
    [Read-Only Permission]
    """
    return registry.search_law(query=query, top_k=top_k)


@mcp.tool()
def get_article(article_id: str) -> Dict[str, Any]:
    """
    Retrieves the verbatim statutory text of a specific article by identifier (e.g. 'Dieu_35').
    [Read-Only Permission]
    """
    return registry.get_article(article_id=article_id)


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
