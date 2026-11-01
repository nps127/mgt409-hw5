"""Facilities: the lease, rent due dates, the landlord, and the physical shop."""

from models import AgentReport

from .base import AgentSpec

SPEC = AgentSpec(
    name="facilities",
    mcp_tools=frozenset({"get_lease", "list_payments", "get_cash_balance", "get_ticket", "get_shop_date"}),
    output_type=AgentReport,
)
