"""
LuatCheck MCP Server (Model Context Protocol).
Provides standardized MCP legal tools via FastMCP.
"""
from typing import Dict, Any, Optional
from mcp.server.fastmcp import FastMCP
from src.tools.legal_tools import LegalToolRegistry

# Initialize FastMCP server
mcp = FastMCP("LuatCheck-Legal-Server")
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
    Saves an advisory case record into episodic memory cache.
    [Reversible Write Permission]
    """
    return registry.save_case(case_id=case_id, summary=summary, client_name=client_name)


@mcp.tool()
def send_summary(
    recipient: str,
    content: str,
    idempotency_key: str,
    user_confirmed: bool = False
) -> Dict[str, Any]:
    """
    Dispatches a legal advisory summary via external communication channels (Email/Webhook).
    [Irreversible Write Permission - Requires Human-in-the-loop confirmation]
    """
    return registry.send_summary(
        recipient=recipient,
        content=content,
        idempotency_key=idempotency_key,
        user_confirmed=user_confirmed
    )


if __name__ == "__main__":
    # Launch stdio transport adhering to the MCP standard
    mcp.run(transport="stdio")
