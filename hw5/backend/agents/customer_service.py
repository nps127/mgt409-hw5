"""Customer service: reply drafts and honest expectations for customers. Never
sees cost or cash, and nothing it writes is sent without a human."""

from models import AgentReport

from .base import AgentSpec

SPEC = AgentSpec(
    name="customer_service",
    mcp_tools=frozenset({"get_ticket", "check_stock", "get_pricing", "list_vendors", "get_shop_date"}),
    output_type=AgentReport,
)
