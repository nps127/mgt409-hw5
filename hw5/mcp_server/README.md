# Campus Customs MCP server

A [FastMCP](https://gofastmcp.com) server that gives every agent on the Campus Customs operations team (boss, inventory, accounting, facilities, customer service) the same set of shop tools. Agents call these tools to look things up instead of guessing.

## Database

Reads **`../data/campus_customs_new.db`**, the working copy. The original `data/campus_customs.db` is never opened.

The tools only return what is stored in the database, or values worked out from it (margin, days overdue). If a row doesn't exist, the tool returns `found: false` rather than making something up. Ten tools are read-only. Three write: `update_ticket`, `record_payment`, and `record_purchase`. Set `CAMPUS_CUSTOMS_DB` to point the server at a test copy instead.

## Tools

| Tool | Table(s) | Read / write | Use it to |
| --- | --- | --- | --- |
| `check_stock(sku, size?)` | `inventory` | read | See how many units of a SKU are on hand (one size, or all sizes) and which aisle they're in |
| `get_lease(lease_id)` | `leases` | read | Get a lease's space, landlord, monthly rent, and next due date |
| `get_pricing(sku)` | `pricing` | read | Get a SKU's unit cost, list price, and per-unit margin |
| `get_shop_date()` | `desk` | read | Get the shop's "today" (use it for every date calculation) |
| `list_tickets(status?)` | `tickets` | read | List tickets, open ones by default, oldest first |
| `get_ticket(ticket_id)` | `tickets` | read | Get one ticket and the SKU / lease / invoice it points to |
| `get_invoice(invoice_id)` | `invoices`, `vendors`, `desk` | read | Get a vendor bill with its vendor and `days_overdue` |
| `list_vendors(specialty?)` | `vendors` | read | Find a vendor and its lead days |
| `get_cash_balance(account?)` | `cash_accounts` | read | Get the balance in `checking` (or another account) |
| `list_payments(kind?, ref_id?)` | `payments` | read | See what's already been paid and who approved it |
| `update_ticket(ticket_id, status, note)` | `tickets` | **write** | Set status (`open`, `in_progress`, `needs_approval`, `waiting_on_vendor`, `resolved`) and append a date-stamped note |
| `record_payment(kind, ref_id, approved_by, account?)` | `payments`, `cash_accounts`, `invoices`/`leases`, `desk` | **write** | Pay an invoice or a month of rent after a named human approves. The amount comes from the database. Double payments, overdrafts, and agent-name approvers are refused. **Not given to any agent.** |
| `record_purchase(vendor_id, sku, size, qty, approved_by, account?)` | `invoices`, `payments`, `cash_accounts`, `vendors`, `inventory`, `pricing`, `desk` | **write** | Buy a reprint/restock after a named human approves. Cost = qty × `unit_cost`. Adds a paid invoice and a payment, lowers cash, and leaves stock unchanged until delivery. **Not given to any agent.** |

Which agent gets which tool is set in `backend/agents/*.py`. `record_payment` and `record_purchase` are blocked for all agents in `backend/shop_mcp.py`. Only the human path calls them: `POST /api/approve` in `backend/main.py`, or `backend/team.py --approve`.

## Run

From `hw5/`, after `pip install -r requirements.txt` (needs Python 3.10+):

```bash
cd mcp_server
../.venv/bin/python server.py           # stdio (for agents / Claude Code)
../.venv/bin/python server.py --http    # HTTP at http://127.0.0.1:8001/mcp
```
