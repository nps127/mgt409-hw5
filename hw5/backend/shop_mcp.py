"""Connection to the campus-customs MCP server.

This is the only way the backend reaches shop data. Agents get the server's
tools through an MCP toolset (filtered per agent), and the human approval path
calls `record_payment` / `record_purchase` through an MCP client. Nothing here queries SQLite.
"""

from __future__ import annotations

import json
import sys
from typing import Any

from fastmcp import Client
from pydantic_ai.mcp import MCPToolset
from pydantic_ai.toolsets import AbstractToolset

from config import MCP_SERVER_DIR

if str(MCP_SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(MCP_SERVER_DIR))

from server import mcp as campus_customs_mcp  # noqa: E402  (FastMCP server object)

# Tools no agent may ever have. Paying money is for a named human only.
HUMAN_ONLY_TOOLS = frozenset({"record_payment", "record_purchase"})

# The server runs in-process and is reached over FastMCP's in-memory MCP
# transport, so there's no separate terminal to start.
_toolset: MCPToolset | None = None


def _shared_toolset() -> MCPToolset:
    global _toolset
    if _toolset is None:
        _toolset = MCPToolset(campus_customs_mcp, id="campus-customs")
    return _toolset


def toolset_for(allowed: frozenset[str]) -> AbstractToolset:
    """The MCP toolset, limited to the tools one agent is allowed to call."""
    blocked = allowed & HUMAN_ONLY_TOOLS
    if blocked:
        raise ValueError(f"agents may not be given {sorted(blocked)}")
    return _shared_toolset().filtered(lambda ctx, tool_def: tool_def.name in allowed)


async def call_tool(name: str, args: dict[str, Any] | None = None) -> dict[str, Any]:
    """Call one MCP tool directly (used by the run loop and the human approval path)."""
    async with Client(campus_customs_mcp) as client:
        result = await client.call_tool(name, args or {}, raise_on_error=False)
    if result.structured_content is not None:
        return result.structured_content
    text = "".join(getattr(block, "text", "") for block in result.content)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"ok": False, "error": text or "empty tool result"}


async def list_tool_names() -> list[str]:
    async with Client(campus_customs_mcp) as client:
        return sorted(tool.name for tool in await client.list_tools())
