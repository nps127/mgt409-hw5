"""Accounting: vendor bills, cash, payment history, pricing, margin, and
discounts. Recommends payments; never makes them."""

from models import AgentReport

from .base import AgentSpec

SPEC = AgentSpec(
    name="accounting",
    mcp_tools=frozenset(
        {
            "get_invoice",
            "get_cash_balance",
            "list_payments",
            "get_pricing",
            "get_lease",
            "list_vendors",
            "get_ticket",
            "list_tickets",
            "get_shop_date",
        }
    ),
    output_type=AgentReport,
)
