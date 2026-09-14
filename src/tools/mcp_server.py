"""
LuatCheck MCP Server (Model Context Protocol)
Cung cấp các công cụ pháp lý chuẩn MCP qua FastMCP
"""
from typing import Dict, Any, Optional
from mcp.server.fastmcp import FastMCP
from src.tools.legal_tools import LegalToolRegistry

# Khởi tạo máy chủ FastMCP
mcp = FastMCP("LuatCheck-Legal-Server")
registry = LegalToolRegistry()


@mcp.tool()
def search_law(query: str, top_k: int = 5) -> Dict[str, Any]:
    """
    Tra cứu điều khoản pháp luật lao động theo câu hỏi hoặc từ khóa ngữ nghĩa.
    [Read-Only Permission]
    """
    return registry.search_law(query=query, top_k=top_k)


@mcp.tool()
def get_article(article_id: str) -> Dict[str, Any]:
    """
    Lấy nguyên văn toàn văn một điều luật cụ thể theo mã định danh (ví dụ: 'Dieu_35').
    [Read-Only Permission]
    """
    return registry.get_article(article_id=article_id)


@mcp.tool()
def save_case(case_id: str, summary: str, client_name: str = "Anonymous") -> Dict[str, Any]:
    """
    Lưu hồ sơ tư vấn vào bộ nhớ tạm.
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
    Gửi tóm tắt tư vấn pháp lý qua kênh giao tiếp bên ngoài (Email/Webhook).
    [Irreversible Write Permission - Yêu cầu xác nhận từ con người]
    """
    return registry.send_summary(
        recipient=recipient,
        content=content,
        idempotency_key=idempotency_key,
        user_confirmed=user_confirmed
    )


if __name__ == "__main__":
    # Khởi chạy qua stdio transport theo chuẩn MCP
    mcp.run(transport="stdio")
