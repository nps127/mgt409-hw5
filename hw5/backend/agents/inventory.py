"""Inventory: stock by SKU and size, shortfalls, aisle locations, and reprint
vendors and lead times."""

from models import AgentReport

from .base import AgentSpec

SPEC = AgentSpec(
    name="inventory",
    mcp_tools=frozenset({"check_stock", "get_pricing", "list_vendors", "get_ticket", "get_shop_date"}),
    output_type=AgentReport,
)
