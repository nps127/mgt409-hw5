"""Run the Campus Customs agent team on open tickets.

From hw5/:
    .venv/bin/python backend/team.py --ticket 101      # one ticket
    .venv/bin/python backend/team.py --all             # every open ticket, oldest first
    .venv/bin/python backend/team.py --approve invoice 501 --by "Natalie Sheppard"

The boss starts every ticket and can delegate to any specialist, and any
specialist can delegate onward. Every agent-loop step is appended to
output/audit_trail.json. Payments only happen through --approve, which is the
human approval path (the agents can't call record_payment).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import uuid
from typing import Any

import config
from agents.base import AgentDeps, RunState, run_agent
from audit import append_step, now_iso
from models import AuditStep, TicketRunResult
from shop_mcp import call_tool


def _boss_prompt(ticket_id: int) -> str:
    return (
        f"Work ticket {ticket_id} from start to finish. Read it with get_ticket, get the shop date, "
        "mark it in_progress, delegate to the specialists it needs, set the final status with "
        "update_ticket, and return your TicketResolution."
    )


async def run_ticket(ticket_id: int) -> TicketRunResult:
    run_id = f"run-{uuid.uuid4().hex[:10]}"
    state = RunState(run_id=run_id, ticket_id=ticket_id)
    deps = AgentDeps(agent="boss", chain=["boss"], state=state)
    try:
        resolution = await run_agent("boss", _boss_prompt(ticket_id), deps)
        return TicketRunResult(
            run_id=run_id,
            ticket_id=ticket_id,
            ok=True,
            resolution=resolution,
            delegations=state.delegations,
            usage=state.usage(),
        )
    except Exception as exc:
        return TicketRunResult(
            run_id=run_id,
            ticket_id=ticket_id,
            ok=False,
            delegations=state.delegations,
            usage=state.usage(),
            error=f"{type(exc).__name__}: {exc}"[:1000],
        )


async def run_open_tickets() -> list[TicketRunResult]:
    """Work every open ticket one at a time (oldest first), so cash decisions
    on later tickets can see the state earlier ones left behind."""
    listing = await call_tool("list_tickets", {"status": "open"})
    results = []
    for ticket in listing.get("tickets", []):
        results.append(await run_ticket(ticket["id"]))
    return results


def _audit_human(tool: str, args: dict[str, Any], result: dict[str, Any], ticket_id: int | None = None) -> None:
    append_step(
        AuditStep(
            time=now_iso(),
            run_id=f"approval-{uuid.uuid4().hex[:10]}",
            ticket_id=ticket_id,
            agent="human",
            agent_run_id=str(args.get("approved_by", "")),
            chain=[],
            depth=0,
            step=0,
            kind="tool_results",
            tool_calls=[{"tool": tool, "args": args}],
            tool_results=[{"tool": tool, "result": result}],
            note=f"human approval by {args.get('approved_by')}; not an agent step",
        )
    )


async def approve_payment(
    kind: str, ref_id: int, approved_by: str, ticket_id: int | None = None
) -> dict[str, Any]:
    """The human approval path: a named person approves, then record_payment runs over MCP."""
    args = {"kind": kind, "ref_id": ref_id, "approved_by": approved_by}
    result = await call_tool("record_payment", args)
    _audit_human("record_payment", args, result, ticket_id)
    return result


async def approve_purchase(
    vendor_id: int, sku: str, size: str, qty: int, approved_by: str, ticket_id: int | None = None
) -> dict[str, Any]:
    """The human approval path for a reprint/restock: record_purchase runs over MCP."""
    args = {"vendor_id": vendor_id, "sku": sku, "size": size, "qty": qty, "approved_by": approved_by}
    result = await call_tool("record_purchase", args)
    _audit_human("record_purchase", args, result, ticket_id)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Campus Customs agent team")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--ticket", type=int, help="work one ticket")
    group.add_argument("--all", action="store_true", help="work every open ticket")
    group.add_argument("--approve", nargs=2, metavar=("KIND", "REF_ID"), help="human: pay an invoice or rent")
    parser.add_argument("--by", help="name of the human approving (required with --approve)")
    args = parser.parse_args()

    if args.approve:
        if not args.by:
            parser.error("--approve needs --by <your name>")
        out: Any = asyncio.run(approve_payment(args.approve[0], int(args.approve[1]), args.by))
    elif args.ticket is not None:
        out = asyncio.run(run_ticket(args.ticket)).model_dump(mode="json")
    else:
        out = [r.model_dump(mode="json") for r in asyncio.run(run_open_tickets())]
    print(json.dumps(out, indent=2, ensure_ascii=False))
    print(f"\nModel: {config.MODEL_NAME} · audit trail: {config.AUDIT_PATH}")


if __name__ == "__main__":
    main()
