"""Campus Customs API for the React dashboard.

Run from this folder (hw5/backend):
    uvicorn main:app --reload --port 8000

Shop data is read and changed only through the campus-customs MCP tools
(backend/shop_mcp.py). The two exceptions are file-level: /api/events reads
output/audit_trail.json, and /api/reset copies the original database file over
the working copy.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import shutil
import uuid
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

import config
from audit import append_step, now_iso
from models import AgentEvent, ApproveRequest, AuditStep, TicketRunResult, TicketSummary
from shop_mcp import call_tool
from team import approve_payment, approve_purchase, run_ticket

import server as mcp_server_module  # the MCP server module (shop_mcp put it on sys.path)

ORIGINAL_DB = config.HW5_DIR / "data" / "campus_customs.db"
WORKING_DB = mcp_server_module.DB_PATH

app = FastAPI(title="Campus Customs API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],  # Vite dev server
    allow_methods=["*"],
    allow_headers=["*"],
)

# One thing at a time touches the working database: an agent run, an approval, or a reset.
_busy = asyncio.Lock()
_running_ticket: int | None = None


def _sha1(path) -> str:
    return hashlib.sha1(path.read_bytes()).hexdigest()


async def _locked(what: str):
    if _busy.locked():
        raise HTTPException(409, f"busy: another run, approval, or reset is in progress ({what} not started)")
    return _busy


@app.get("/api/health")
async def health() -> dict[str, Any]:
    return {
        "ok": True,
        "model": config.MODEL_NAME,
        "portkey_key_set": bool(os.getenv("PORTKEY_API_KEY", "").strip()),
        "database": str(WORKING_DB.relative_to(config.HW5_DIR)) if WORKING_DB.is_relative_to(config.HW5_DIR) else str(WORKING_DB),
        "busy": _busy.locked(),
        "running_ticket": _running_ticket,
    }


@app.get("/api/tickets", response_model=list[TicketSummary])
async def tickets() -> list[TicketSummary]:
    """Every ticket, with its exact status and a simple open/resolved state."""
    data = await call_tool("list_tickets", {"status": None})
    return [
        TicketSummary(**{k: t.get(k) for k in TicketSummary.model_fields if k != "state"},
                      state="resolved" if t["status"] == "resolved" else "open")
        for t in data.get("tickets", [])
    ]


@app.post("/api/tickets/{ticket_id}/run", response_model=TicketRunResult)
async def run(ticket_id: int) -> TicketRunResult:
    """Run the agent team on one ticket and wait for the boss's resolution."""
    found = await call_tool("get_ticket", {"ticket_id": ticket_id})
    if not found.get("found"):
        raise HTTPException(404, f"no ticket with id {ticket_id}")
    global _running_ticket
    lock = await _locked("run")
    async with lock:
        _running_ticket = ticket_id
        try:
            result = await run_ticket(ticket_id)
            if result.ok and result.resolution:
                # The run is finished, so the ticket is resolved on the board. The boss's
                # own status and any approvals still waiting go in the note.
                waiting = [a.kind for a in result.resolution.approvals_needed]
                note = f"Agent run {result.run_id} finished (boss set {result.resolution.final_status})."
                if waiting:
                    note += f" Waiting on human approval: {', '.join(waiting)}."
                await call_tool("update_ticket", {"ticket_id": ticket_id, "status": "resolved", "note": note})
            return result
        finally:
            _running_ticket = None


def _event(row: dict[str, Any]) -> AgentEvent:
    said = row.get("text")
    output = row.get("output") or {}
    if row.get("kind") == "final":
        said = output.get("summary") or output.get("answer") or said
    calls = row.get("tool_calls") or []
    if row.get("kind") == "tool_results":  # show what came back, keyed by tool
        calls = calls or [{"tool": r.get("tool")} for r in row.get("tool_results", [])]
    return AgentEvent(
        time=row.get("time", ""),
        run_id=row.get("run_id", ""),
        ticket_id=row.get("ticket_id"),
        agent=row.get("agent", ""),
        chain=row.get("chain", []),
        kind=row.get("kind", ""),
        said=said,
        tools_used=list(dict.fromkeys(
            c["tool"] for c in calls if c.get("tool") and not c["tool"].startswith("final_result")
        )),
        tool_calls=calls,
        results=[
            {"tool": r.get("tool"), "result": str(r.get("result", r.get("retry", "")))[:240]}
            for r in row.get("tool_results", [])
        ],
        note=row.get("note"),
    )


@app.get("/api/events", response_model=list[AgentEvent])
async def events(
    limit: int = Query(50, ge=1, le=500),
    ticket_id: int | None = None,
    run_id: str | None = None,
    since: str | None = Query(None, description="Only events after this ISO time (for polling)."),
) -> list[AgentEvent]:
    """Most recent agent events (oldest first within the window) from the audit trail."""
    path = config.AUDIT_PATH
    if not path.exists() or path.stat().st_size == 0:
        return []
    try:
        rows = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        raise HTTPException(503, "audit trail is being written; try again")
    # These rows add nothing to the board on their own.
    rows = [r for r in rows if r.get("kind") not in ("model_request", "user_prompt")]
    if ticket_id is not None:
        rows = [r for r in rows if r.get("ticket_id") == ticket_id]
    if run_id:
        rows = [r for r in rows if r.get("run_id") == run_id]
    if since:
        rows = [r for r in rows if r.get("time", "") > since]
    return [_event(r) for r in rows[-limit:]]


def _audit_rows() -> list[dict[str, Any]]:
    path = config.AUDIT_PATH
    if not path.exists() or path.stat().st_size == 0:
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        raise HTTPException(503, "audit trail is being written; try again")


def _approval_done(approval: dict[str, Any], human_rows: list[dict[str, Any]]) -> bool:
    for row in human_rows:
        for res in row.get("tool_results", []):
            if not isinstance(res.get("result"), dict) or not res["result"].get("ok"):
                continue
            args = (row.get("tool_calls") or [{}])[0].get("args", {})
            kind = approval.get("kind")
            if res.get("tool") == "record_payment":
                want = {"invoice_payment": "invoice", "rent_payment": "rent"}.get(kind)
                if want and args.get("kind") == want and args.get("ref_id") == approval.get("ref_id"):
                    return True
            if res.get("tool") == "record_purchase" and kind == "reprint_order":
                if (args.get("sku") or "").upper() == (approval.get("sku") or "").upper() and (
                    args.get("size") or ""
                ).upper() == (approval.get("size") or "").upper():
                    return True
    return False


@app.get("/api/tickets/{ticket_id}/summary")
async def ticket_summary(ticket_id: int) -> dict[str, Any]:
    """The latest agent run on a ticket: the boss's resolution, approvals (and whether a
    human has approved them since), and a short per-agent summary."""
    rows = _audit_rows()
    # A reset puts the database back, so runs from before the last reset no longer apply.
    resets = [r["time"] for r in rows if str(r.get("run_id", "")).startswith("reset-")]
    if resets:
        rows = [r for r in rows if r.get("time", "") > resets[-1]]
    runs = [r for r in rows if r.get("ticket_id") == ticket_id and str(r.get("run_id", "")).startswith("run-")]
    if not runs:
        return {"ticket_id": ticket_id, "run_id": None, "running": _running_ticket == ticket_id, "agents": [], "approvals": []}
    run_id = runs[-1]["run_id"]
    run_rows = [r for r in runs if r["run_id"] == run_id]
    started = run_rows[0]["time"]

    agents: dict[str, dict[str, Any]] = {}
    resolution = None
    finished, error = False, None
    for r in run_rows:
        a = agents.setdefault(
            r["agent"],
            {"agent": r["agent"], "asked_by": [], "tasks": [], "tools": [], "delegated_to": [], "answer": None, "steps": 0, "tokens": 0},
        )
        if r["kind"] == "run_start":
            if r.get("parent_agent") and r["parent_agent"] not in a["asked_by"]:
                a["asked_by"].append(r["parent_agent"])
            a["tasks"].append(r.get("text"))
        if r["kind"] == "model_response":
            a["steps"] += 1
            a["tokens"] += sum((r.get("usage") or {}).values())
            for c in r.get("tool_calls", []):
                name = c.get("tool", "")
                if name and name != "delegate" and not name.startswith("final_result") and name not in a["tools"]:
                    a["tools"].append(name)
        if r["kind"] == "delegation" and not str(r.get("note", "")).startswith("refused"):
            to = (r.get("tool_calls") or [{}])[0].get("to")
            if to and to not in a["delegated_to"]:
                a["delegated_to"].append(to)
        if r["kind"] == "final":
            out = r.get("output") or {}
            a["answer"] = out.get("answer") or out.get("summary")
            if r["agent"] == "boss" and r.get("depth") == 0:
                resolution = out
        if r["agent"] == "boss" and r.get("depth") == 0 and r["kind"] in ("run_end", "error"):
            finished = True
            if r["kind"] == "error":
                error = r.get("note")

    human = [r for r in rows if r.get("agent") == "human" and r.get("time", "") > started]
    approvals = []
    for i, ap in enumerate((resolution or {}).get("approvals_needed", [])):
        approvals.append({**ap, "id": i, "approved": _approval_done(ap, human)})

    return {
        "ticket_id": ticket_id,
        "run_id": run_id,
        "started": started,
        "running": _running_ticket == ticket_id,
        "interrupted": not finished and _running_ticket != ticket_id,
        "error": error,
        "resolution": resolution,
        "agents": list(agents.values()),
        "approvals": approvals,
        "run_usage": run_rows[-1].get("run_usage", {}),
    }


@app.post("/api/approve")
async def approve(body: ApproveRequest) -> dict[str, Any]:
    """A human clicked Approve. This is the only route that moves money (via MCP)."""
    lock = await _locked("approval")
    async with lock:
        if body.action == "payment":
            if body.kind is None or body.ref_id is None:
                raise HTTPException(422, "payment needs kind ('invoice' or 'rent') and ref_id")
            result = await approve_payment(body.kind, body.ref_id, body.approved_by, body.ticket_id)
        else:
            if None in (body.vendor_id, body.sku, body.size, body.qty):
                raise HTTPException(422, "purchase needs vendor_id, sku, size, and qty")
            result = await approve_purchase(
                body.vendor_id, body.sku, body.size, body.qty, body.approved_by, body.ticket_id
            )
    if not result.get("ok"):
        raise HTTPException(400, result.get("error", "approval refused"))
    return result


@app.get("/api/cash")
async def cash() -> dict[str, Any]:
    """Current checking balance from cash_accounts."""
    data = await call_tool("get_cash_balance", {"account": "checking"})
    if not data.get("found"):
        raise HTTPException(404, "no checking account")
    return data["cash"]


@app.get("/api/payments")
async def payments() -> list[dict[str, Any]]:
    """Money already paid out (newest first), from the payments table via list_payments."""
    data = await call_tool("list_payments", {})
    return data.get("payments", [])


@app.post("/api/reset")
async def reset() -> dict[str, Any]:
    """Copy the original database over the working copy for a fresh run.
    The audit trail is kept (a reset row is appended), never wiped."""
    if WORKING_DB.resolve() == ORIGINAL_DB.resolve():
        raise HTTPException(500, "working database points at the original; refusing to reset")
    if not ORIGINAL_DB.exists():
        raise HTTPException(500, f"original database missing: {ORIGINAL_DB.name}")
    lock = await _locked("reset")
    async with lock:
        before = _sha1(WORKING_DB) if WORKING_DB.exists() else None
        tmp = WORKING_DB.with_suffix(".db.tmp")
        shutil.copyfile(ORIGINAL_DB, tmp)
        tmp.replace(WORKING_DB)
        after = _sha1(WORKING_DB)
        append_step(
            AuditStep(
                time=now_iso(), run_id=f"reset-{uuid.uuid4().hex[:10]}", ticket_id=None, agent="human",
                agent_run_id="reset", chain=[], depth=0, step=0, kind="run_end",
                note=f"database reset to original (sha1 {before} -> {after})",
            )
        )
    return {"ok": after == _sha1(ORIGINAL_DB), "sha1_before": before, "sha1_after": after}
