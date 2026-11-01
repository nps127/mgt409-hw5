"""Campus Customs MCP server — HW5.

Shared tools for every agent on the Campus Customs operations team. Reads the
working copy of the shop database at ../data/campus_customs_new.db (the
original campus_customs.db is never touched).

Tools only return what is in the database. If a row isn't there, the tool
says so instead of guessing. Most tools are read-only. Three tools write:
`update_ticket` (ticket status and notes), and `record_payment` and
`record_purchase` (money out, which needs a named human approver; neither is
ever given to the agents).

Run from this folder (stdio):  ../.venv/bin/python server.py
Run (HTTP):                    ../.venv/bin/python server.py --http
HTTP URL:                      http://127.0.0.1:8001/mcp
"""

from __future__ import annotations

import argparse
import calendar
import os
import sqlite3
from datetime import date
from pathlib import Path

from fastmcp import FastMCP

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
# CAMPUS_CUSTOMS_DB lets tests point the server at a throwaway copy.
DB_PATH = Path(os.getenv("CAMPUS_CUSTOMS_DB", ROOT / "data" / "campus_customs_new.db"))

AGENT_NAMES = {"boss", "inventory", "accounting", "facilities", "customer_service"}
TICKET_STATUSES = ("open", "in_progress", "needs_approval", "waiting_on_vendor", "resolved")

mcp = FastMCP("campus-customs")


def _read(sql: str, params: tuple = ()) -> list[dict]:
    """Run a read-only query. Opening with mode=ro means a missing file errors
    out instead of SQLite quietly creating an empty database."""
    uri = f"{DB_PATH.as_uri()}?mode=ro"
    with sqlite3.connect(uri, uri=True) as conn:
        conn.row_factory = sqlite3.Row
        return [dict(row) for row in conn.execute(sql, params)]


def _connect_rw() -> sqlite3.Connection:
    """Read-write connection for the two write tools. mode=rw still refuses to
    create a missing file."""
    conn = sqlite3.connect(f"{DB_PATH.as_uri()}?mode=rw", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _shop_today() -> str:
    rows = _read("SELECT date_today FROM desk LIMIT 1")
    return rows[0]["date_today"] if rows else date.today().isoformat()


def _add_month(iso_day: str) -> str:
    d = date.fromisoformat(iso_day)
    year, month = (d.year + 1, 1) if d.month == 12 else (d.year, d.month + 1)
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day).isoformat()


@mcp.tool
def check_stock(sku: str, size: str | None = None) -> dict:
    """Look up how many units of a product are on hand, by SKU and size.

    Reads the `inventory` table. Pass `size` (S, M, L, XL, or OS for one-size
    items) to check one size, or leave it out to see every size of the SKU.
    Returns the matching rows with name, size, qty, and location. If nothing
    matches, `found` is false and `rows` is empty.
    """
    sku = sku.strip().upper()
    if size:
        size = size.strip().upper()
        rows = _read(
            "SELECT sku, name, size, qty, location FROM inventory "
            "WHERE sku = ? AND size = ?",
            (sku, size),
        )
    else:
        rows = _read(
            "SELECT sku, name, size, qty, location FROM inventory "
            "WHERE sku = ? ORDER BY rowid",
            (sku,),
        )
    return {"sku": sku, "size": size, "found": bool(rows), "rows": rows}


@mcp.tool
def get_lease(lease_id: int) -> dict:
    """Look up a shop lease by id: space, landlord, monthly rent, and next due date.

    Reads the `leases` table. Use the `lease_id` on a rent ticket. If no
    lease has that id, `found` is false and `lease` is null.
    """
    rows = _read(
        "SELECT id, space_name, landlord, monthly_rent, next_due, notes "
        "FROM leases WHERE id = ?",
        (lease_id,),
    )
    return {"lease_id": lease_id, "found": bool(rows), "lease": rows[0] if rows else None}


@mcp.tool
def get_pricing(sku: str) -> dict:
    """Look up a product's unit cost and list price by SKU.

    Reads the `pricing` table. Also returns the per-unit margin (list price
    minus unit cost), worked out from those two stored numbers, so a discount
    can be checked against what the shop actually earns per item. If the SKU
    has no pricing row, `found` is false and `pricing` is null.
    """
    sku = sku.strip().upper()
    rows = _read("SELECT sku, unit_cost, list_price FROM pricing WHERE sku = ?", (sku,))
    if not rows:
        return {"sku": sku, "found": False, "pricing": None}
    row = rows[0]
    row["unit_margin"] = round(row["list_price"] - row["unit_cost"], 2)
    return {"sku": sku, "found": True, "pricing": row}


@mcp.tool
def get_shop_date() -> dict:
    """Get the shop's "today" from the `desk` table.

    Use this date for every due-date, overdue, and lead-time calculation, not
    the computer's clock. Also returns any desk notes.
    """
    rows = _read("SELECT date_today, notes FROM desk LIMIT 1")
    return {"found": bool(rows), "desk": rows[0] if rows else None}


@mcp.tool
def list_tickets(status: str | None = "open") -> dict:
    """List tickets from the `tickets` table, oldest first.

    Pass a `status` (open, in_progress, needs_approval, waiting_on_vendor,
    resolved) to filter, or null for every ticket. Defaults to open tickets.
    """
    if status:
        rows = _read(
            "SELECT * FROM tickets WHERE status = ? ORDER BY created_at, id",
            (status.strip().lower(),),
        )
    else:
        rows = _read("SELECT * FROM tickets ORDER BY created_at, id")
    return {"status": status, "count": len(rows), "tickets": rows}


@mcp.tool
def get_ticket(ticket_id: int) -> dict:
    """Get one ticket by id from the `tickets` table.

    The `sku`/`size`/`qty`, `lease_id`, and `invoice_id` fields point to the
    records the ticket needs. If no ticket has that id, `found` is false.
    """
    rows = _read("SELECT * FROM tickets WHERE id = ?", (ticket_id,))
    return {"ticket_id": ticket_id, "found": bool(rows), "ticket": rows[0] if rows else None}


@mcp.tool
def get_invoice(invoice_id: int) -> dict:
    """Get a vendor invoice and its vendor, from `invoices` joined to `vendors`.

    Returns amount, due date, status, description, and the vendor's name,
    specialty, and lead days. Also returns `days_overdue` (shop date minus due
    date, 0 if not yet due) using the `desk` date. If no invoice has that id,
    `found` is false.
    """
    rows = _read(
        "SELECT i.id, i.vendor_id, i.amount, i.due_date, i.status, i.description, "
        "v.name AS vendor_name, v.specialty AS vendor_specialty, v.lead_days AS vendor_lead_days "
        "FROM invoices i JOIN vendors v ON v.id = i.vendor_id WHERE i.id = ?",
        (invoice_id,),
    )
    if not rows:
        return {"invoice_id": invoice_id, "found": False, "invoice": None}
    row = rows[0]
    today = _shop_today()
    late = (date.fromisoformat(today) - date.fromisoformat(row["due_date"])).days
    row["shop_date"] = today
    row["days_overdue"] = max(late, 0) if row["status"] != "paid" else 0
    return {"invoice_id": invoice_id, "found": True, "invoice": row}


@mcp.tool
def list_vendors(specialty: str | None = None) -> dict:
    """List vendors from the `vendors` table: name, specialty, and lead days.

    Pass part of a `specialty` (for example "apparel") to filter. Lead days are
    how long a restock or delivery takes from the day it is ordered.
    """
    if specialty:
        rows = _read(
            "SELECT id, name, specialty, lead_days FROM vendors "
            "WHERE specialty LIKE ? ORDER BY id",
            (f"%{specialty.strip()}%",),
        )
    else:
        rows = _read("SELECT id, name, specialty, lead_days FROM vendors ORDER BY id")
    return {"specialty": specialty, "count": len(rows), "vendors": rows}


@mcp.tool
def get_cash_balance(account: str = "checking") -> dict:
    """Get a cash account's balance and as-of date from `cash_accounts`.

    Check this before recommending any payment. If the account doesn't exist,
    `found` is false.
    """
    rows = _read(
        "SELECT name, balance, date FROM cash_accounts WHERE name = ?",
        (account.strip().lower(),),
    )
    return {"account": account, "found": bool(rows), "cash": rows[0] if rows else None}


@mcp.tool
def list_payments(kind: str | None = None, ref_id: int | None = None) -> dict:
    """List money already paid out, from the `payments` table, newest first.

    Filter by `kind` ("invoice" or "rent") and/or `ref_id` (the invoice id or
    lease id). Check this before recommending a payment so nothing is paid twice.
    Each row shows who approved it (`approved_by`).
    """
    sql, params = "SELECT * FROM payments WHERE 1 = 1", []
    if kind:
        sql += " AND kind = ?"
        params.append(kind.strip().lower())
    if ref_id is not None:
        sql += " AND ref_id = ?"
        params.append(ref_id)
    rows = _read(sql + " ORDER BY paid_at DESC, id DESC", tuple(params))
    return {"kind": kind, "ref_id": ref_id, "count": len(rows), "payments": rows}


@mcp.tool
def update_ticket(ticket_id: int, status: str, note: str) -> dict:
    """Change a ticket's status and add a note to it (writes the `tickets` table).

    `status` must be one of: open, in_progress, needs_approval,
    waiting_on_vendor, resolved. `note` is required and is appended to the
    ticket's existing notes (old notes are kept), stamped with the shop date.
    Returns the ticket before and after the change.
    """
    status = status.strip().lower()
    note = " ".join(note.split())
    if status not in TICKET_STATUSES:
        return {"ok": False, "error": f"status must be one of {list(TICKET_STATUSES)}"}
    if not note:
        return {"ok": False, "error": "a note explaining the change is required"}
    before = _read("SELECT * FROM tickets WHERE id = ?", (ticket_id,))
    if not before:
        return {"ok": False, "error": f"no ticket with id {ticket_id}"}
    stamped = f"[{_shop_today()} {status}] {note}"
    with _connect_rw() as conn:
        conn.execute(
            "UPDATE tickets SET status = ?, "
            "notes = CASE WHEN notes IS NULL OR notes = '' THEN ? ELSE notes || ' | ' || ? END "
            "WHERE id = ?",
            (status, stamped, stamped, ticket_id),
        )
    after = _read("SELECT * FROM tickets WHERE id = ?", (ticket_id,))
    return {"ok": True, "before": before[0], "after": after[0]}


@mcp.tool
def record_payment(kind: str, ref_id: int, approved_by: str, account: str = "checking") -> dict:
    """Pay a vendor invoice or a month of rent, after a human approved it.

    Writes `payments`, lowers the `cash_accounts` balance, and then either marks
    the invoice `paid` (kind "invoice", ref_id = invoice id) or moves the lease's
    `next_due` forward one month (kind "rent", ref_id = lease id). The amount is
    read from the invoice or lease, never passed in. Refuses if the approver is
    blank or an agent name, the bill is already paid, or cash would go below zero.
    The agent team does not get this tool; only the human approval path calls it.
    """
    kind = kind.strip().lower()
    approver = " ".join(approved_by.split())
    if not approver or approver.lower().replace(" ", "_") in AGENT_NAMES:
        return {"ok": False, "error": "approved_by must name the human who approved this payment"}
    if kind not in ("invoice", "rent"):
        return {"ok": False, "error": 'kind must be "invoice" or "rent"'}

    today = _shop_today()
    with _connect_rw() as conn:
        cash = conn.execute(
            "SELECT balance FROM cash_accounts WHERE name = ?", (account.strip().lower(),)
        ).fetchone()
        if cash is None:
            return {"ok": False, "error": f"no cash account named {account!r}"}

        if kind == "invoice":
            bill = conn.execute("SELECT amount, status FROM invoices WHERE id = ?", (ref_id,)).fetchone()
            if bill is None:
                return {"ok": False, "error": f"no invoice with id {ref_id}"}
            if bill["status"] == "paid":
                return {"ok": False, "error": f"invoice {ref_id} is already paid"}
            amount = bill["amount"]
        else:
            lease = conn.execute("SELECT monthly_rent, next_due FROM leases WHERE id = ?", (ref_id,)).fetchone()
            if lease is None:
                return {"ok": False, "error": f"no lease with id {ref_id}"}
            # Rent counts as paid once the next due date has moved past this month's.
            if lease["next_due"] > _add_month(today):
                return {"ok": False, "error": f"rent on lease {ref_id} is already paid through {lease['next_due']}"}
            amount = lease["monthly_rent"]

        if cash["balance"] < amount:
            return {"ok": False, "error": f"not enough cash: {cash['balance']:.2f} < {amount:.2f}"}

        cur = conn.execute(
            "INSERT INTO payments (kind, ref_id, amount, account, paid_at, approved_by) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (kind, ref_id, amount, account.strip().lower(), today, approver),
        )
        conn.execute(
            "UPDATE cash_accounts SET balance = balance - ?, date = ? WHERE name = ?",
            (amount, today, account.strip().lower()),
        )
        if kind == "invoice":
            conn.execute("UPDATE invoices SET status = 'paid' WHERE id = ?", (ref_id,))
        else:
            conn.execute("UPDATE leases SET next_due = ? WHERE id = ?", (_add_month(lease["next_due"]), ref_id))
        payment_id = cur.lastrowid

    payment = _read("SELECT * FROM payments WHERE id = ?", (payment_id,))[0]
    balance = _read("SELECT balance FROM cash_accounts WHERE name = ?", (account.strip().lower(),))[0]
    return {"ok": True, "payment": payment, "new_balance": balance["balance"]}


@mcp.tool
def record_purchase(vendor_id: int, sku: str, size: str, qty: int, approved_by: str, account: str = "checking") -> dict:
    """Buy a reprint or restock from a vendor, after a human approved it.

    The cost is `qty` x the SKU's `unit_cost` from `pricing`, never passed in.
    Writes a new `invoices` row (status `paid`, due on the shop date, with a
    description of what was bought), a matching `payments` row (kind
    "invoice"), and lowers the `cash_accounts` balance. Stock in `inventory`
    does not change until the goods arrive. Refuses if the approver is blank or
    an agent name, the vendor or SKU/size doesn't exist, qty isn't 1-500, or
    cash would go below zero. The agent team does not get this tool.
    """
    approver = " ".join(approved_by.split())
    if not approver or approver.lower().replace(" ", "_") in AGENT_NAMES:
        return {"ok": False, "error": "approved_by must name the human who approved this purchase"}
    if not 1 <= qty <= 500:
        return {"ok": False, "error": "qty must be between 1 and 500"}
    sku, size, acct = sku.strip().upper(), size.strip().upper(), account.strip().lower()
    today = _shop_today()
    with _connect_rw() as conn:
        vendor = conn.execute("SELECT name FROM vendors WHERE id = ?", (vendor_id,)).fetchone()
        if vendor is None:
            return {"ok": False, "error": f"no vendor with id {vendor_id}"}
        item = conn.execute("SELECT name FROM inventory WHERE sku = ? AND size = ?", (sku, size)).fetchone()
        price = conn.execute("SELECT unit_cost FROM pricing WHERE sku = ?", (sku,)).fetchone()
        if item is None or price is None:
            return {"ok": False, "error": f"no stock or pricing row for {sku} {size}"}
        cash = conn.execute("SELECT balance FROM cash_accounts WHERE name = ?", (acct,)).fetchone()
        if cash is None:
            return {"ok": False, "error": f"no cash account named {account!r}"}
        amount = round(qty * price["unit_cost"], 2)
        if cash["balance"] < amount:
            return {"ok": False, "error": f"not enough cash: {cash['balance']:.2f} < {amount:.2f}"}
        inv = conn.execute(
            "INSERT INTO invoices (vendor_id, amount, due_date, status, description) VALUES (?, ?, ?, 'paid', ?)",
            (vendor_id, amount, today, f"Purchase {qty} x {sku} {size} ({item['name']}), approved by {approver}"),
        )
        pay = conn.execute(
            "INSERT INTO payments (kind, ref_id, amount, account, paid_at, approved_by) VALUES ('invoice', ?, ?, ?, ?, ?)",
            (inv.lastrowid, amount, acct, today, approver),
        )
        conn.execute("UPDATE cash_accounts SET balance = balance - ?, date = ? WHERE name = ?", (amount, today, acct))
        invoice_id, payment_id = inv.lastrowid, pay.lastrowid

    return {
        "ok": True,
        "invoice": _read("SELECT * FROM invoices WHERE id = ?", (invoice_id,))[0],
        "payment": _read("SELECT * FROM payments WHERE id = ?", (payment_id,))[0],
        "new_balance": _read("SELECT balance FROM cash_accounts WHERE name = ?", (acct,))[0]["balance"],
        "note": "Stock is unchanged until the goods arrive.",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Campus Customs MCP server")
    parser.add_argument(
        "--http",
        action="store_true",
        help="Serve Streamable HTTP on port 8001 (keeps FastAPI free on 8000)",
    )
    args = parser.parse_args()
    if args.http:
        mcp.run(transport="http", host="127.0.0.1", port=8001)
    else:
        mcp.run()
