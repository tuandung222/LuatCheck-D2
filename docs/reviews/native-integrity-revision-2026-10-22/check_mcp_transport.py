"""Local MCP transport check only; no model inference or external writes."""
import asyncio
import json
import os
import sys
from pathlib import Path
from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters

async def check():
    params = StdioServerParameters(command=sys.executable, args=["-m", "src.tools.mcp_server"],
                                   cwd=str(Path.cwd()), env={"PYTHONPATH": str(Path.cwd()),
                                                            "MODEL_ENDPOINT": "http://127.0.0.1:1"})
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write, read_timeout_seconds=10) as session:
            await session.initialize()
            tools = await session.list_tools()
            schemas = {tool.name: tool.input_schema for tool in tools.tools}
            assert set(schemas) == {"search_law", "get_article", "save_case", "send_summary"}
            assert "user_confirmed" not in schemas["send_summary"]["properties"]
            assert "approve_proposal" not in schemas
            def decoded(result):
                assert not result.is_error, result
                return json.loads(next(c.text for c in result.content if c.type == "text"))
            article = decoded(await session.call_tool("get_article", {"article_id": "Dieu_25"}))
            assert article["status"] == "success" and article["article_id"] == "Dieu_25"
            search = decoded(await session.call_tool("search_law", {"query": "thử việc", "top_k": 2}))
            assert search["status"] == "success"
            blocked = decoded(await session.call_tool("save_case", {"case_id": "protocol-check", "summary": "No write"}))
            assert blocked["status"] == "blocked_unverified_write"
            proposal = decoded(await session.call_tool("send_summary", {
                "recipient": "protocol-check@example.invalid", "content": "No delivery",
                "idempotency_key": "protocol-check"}))
            assert proposal["status"] == "blocked_by_permission_gate"
            assert "approval_token" not in proposal
            return {"check": "real_local_MCP_stdio_transport", "tools": sorted(schemas),
                    "article_lookup": article["status"], "search": search["status"],
                    "unverified_write": blocked["status"], "summary": proposal["status"],
                    "inference_executed": False, "external_delivery": False,
                    "empirical_model_evidence": False}
if __name__ == "__main__":
    print(json.dumps(asyncio.run(asyncio.wait_for(check(), 25)), indent=2))
