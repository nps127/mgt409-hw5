"""Boss: reads the ticket, routes it, checks the specialists' work, sets the
ticket status, and writes the TicketResolution."""

import config
from models import TicketResolution

from .base import AgentSpec

SPEC = AgentSpec(
    name="boss",
    mcp_tools=frozenset({"list_tickets", "get_ticket", "get_shop_date", "get_cash_balance", "update_ticket"}),
    output_type=TicketResolution,  # an AgentReport instead when another agent delegates to the boss
    request_limit=config.BOSS_REQUEST_LIMIT,
)
