"""Data types for the Campus Customs agent team.

Agents return these as structured output, the delegate tool passes them
between agents, and the audit trail stores AuditStep rows.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

AgentName = Literal["boss", "inventory", "accounting", "facilities", "customer_service"]
AGENT_NAMES: tuple[str, ...] = ("boss", "inventory", "accounting", "facilities", "customer_service")

TicketStatus = Literal["open", "in_progress", "needs_approval", "waiting_on_vendor", "resolved"]


class ApprovalRequest(BaseModel):
    """Something only a human may decide: paying money, giving a discount,
    ordering a reprint, or sending a message to a customer or landlord."""

    kind: Literal["invoice_payment", "rent_payment", "discount", "reprint_order", "customer_message", "other"]
    ticket_id: int | None = None
    ref_id: int | None = Field(
        default=None, description="Invoice id for invoice_payment, lease id for rent_payment."
    )
    amount: float | None = Field(default=None, description="Dollar amount, taken from a tool result.")
    summary: str = Field(description="One or two sentences: what to approve and why.")
    risks: list[str] = Field(default_factory=list, description="What could go wrong (cash, margin, timing).")
    # reprint_order only: what to buy, so the human can approve it in one click
    vendor_id: int | None = Field(default=None, description="reprint_order: vendor id from list_vendors.")
    sku: str | None = Field(default=None, description="reprint_order: SKU to reprint.")
    size: str | None = Field(default=None, description="reprint_order: size to reprint.")
    qty: int | None = Field(default=None, description="reprint_order: units to reprint.")


class AgentReport(BaseModel):
    """What a specialist (or the boss, when delegated to) hands back to whoever asked."""

    agent: AgentName
    answer: str = Field(description="Direct answer to the task, in plain words.")
    facts: list[str] = Field(
        default_factory=list,
        description="Each fact used, with the tool and value it came from, e.g. 'check_stock: CC-TEE-WHITE S qty 0'.",
    )
    recommended_actions: list[str] = Field(default_factory=list)
    approvals_needed: list[ApprovalRequest] = Field(default_factory=list)
    open_questions: list[str] = Field(
        default_factory=list, description="Anything the tools could not answer."
    )


class TicketResolution(BaseModel):
    """The boss's final word on one ticket."""

    ticket_id: int
    final_status: TicketStatus
    summary: str = Field(description="What was found and decided, in 2-5 sentences.")
    agents_consulted: list[AgentName] = Field(default_factory=list)
    facts: list[str] = Field(default_factory=list)
    actions_taken: list[str] = Field(
        default_factory=list, description="Only things a tool actually did, e.g. update_ticket."
    )
    approvals_needed: list[ApprovalRequest] = Field(default_factory=list)
    customer_reply_draft: str | None = Field(
        default=None, description="Draft only. A human reviews it before anything is sent."
    )
    open_questions: list[str] = Field(default_factory=list)


class Delegation(BaseModel):
    """One hand-off from one agent to another."""

    from_agent: AgentName
    to_agent: AgentName
    task: str
    depth: int
    status: Literal["done", "refused", "error"]
    report: AgentReport | None = None
    error: str | None = None


class AuditStep(BaseModel):
    """One row in output/audit_trail.json. One row per agent-loop step."""

    time: str
    run_id: str
    ticket_id: int | None
    agent: AgentName | Literal["human"]
    agent_run_id: str = Field(description="Unique per agent run, so nested delegations can be told apart.")
    parent_agent: AgentName | None = None
    chain: list[AgentName] = Field(description="Who delegated to whom to reach this agent, boss first.")
    depth: int
    step: int = Field(description="Step number inside this agent's loop, starting at 0.")
    kind: Literal[
        "run_start",
        "user_prompt",
        "model_request",
        "model_response",
        "tool_results",
        "delegation",
        "final",
        "error",
        "run_end",
    ]
    model: str | None = None
    text: str | None = None
    thinking: str | None = None
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    tool_results: list[dict[str, Any]] = Field(default_factory=list)
    output: dict[str, Any] | None = None
    usage: dict[str, int] = Field(default_factory=dict)
    run_usage: dict[str, int] = Field(
        default_factory=dict, description="Running total for the whole ticket, across every agent."
    )
    note: str | None = None


class TicketRunResult(BaseModel):
    """What run_ticket returns: the boss's resolution plus how it got there."""

    run_id: str
    ticket_id: int
    ok: bool
    resolution: TicketResolution | None = None
    delegations: list[Delegation] = Field(default_factory=list)
    usage: dict[str, int] = Field(default_factory=dict)
    error: str | None = None


# --- API (backend/main.py) ------------------------------------------------------


class TicketSummary(BaseModel):
    id: int
    type: str
    requester: str
    subject: str
    status: str = Field(description="Exact status in the tickets table.")
    state: Literal["open", "resolved"] = Field(description="'resolved' only when status is resolved.")
    notes: str | None = None
    created_at: str


class AgentEvent(BaseModel):
    """One audit row, trimmed for the dashboard board."""

    time: str
    run_id: str
    ticket_id: int | None = None
    agent: str
    chain: list[str] = Field(default_factory=list)
    kind: str
    said: str | None = Field(default=None, description="What the agent wrote, or its final answer/summary.")
    tools_used: list[str] = Field(default_factory=list)
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    results: list[dict[str, Any]] = Field(default_factory=list, description="Tool results, trimmed.")
    note: str | None = None


class ApproveRequest(BaseModel):
    """A human clicked Approve. `payment` pays an invoice or rent; `purchase` buys a reprint."""

    action: Literal["payment", "purchase"]
    approved_by: str = Field(min_length=2, max_length=80, description="The human's name.")
    ticket_id: int | None = None
    # payment
    kind: Literal["invoice", "rent"] | None = None
    ref_id: int | None = Field(default=None, description="Invoice id or lease id.")
    # purchase
    vendor_id: int | None = None
    sku: str | None = None
    size: str | None = None
    qty: int | None = Field(default=None, ge=1, le=500)
