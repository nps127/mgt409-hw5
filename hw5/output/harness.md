# Harness — HW5 Campus Customs multi-agent operations

Working notes on the data, tools, and agents. Updated problem by problem; complete as of Problem 9.

**Contents:** 1 Database tables · 2 The three tickets · 3 MCP tools · 4 The five agents · 5 Safety rules · 6 API routes · 7 Dashboard · 8 Problem 9 full run · 9 Notes

---

## 1. Database

- **Original:** `data/campus_customs.db`. This is never edited.
- **Working copy:** `data/campus_customs_new.db`. All runs and approvals write here. `POST /api/reset` (the dashboard's **Reset shop** button) copies the original back over it byte-for-byte (same SHA-1, `f447ca6a…`).
- **Shop "today":** `2026-08-31`, from the `desk` table. Agents should use this date for "due soon" and "overdue", not the computer's clock.

### Tables and fields

Rows are counted in the original, then after the Problem 9 run.

| Table | Rows | Fields | Why it matters for the agents |
| --- | --- | --- | --- |
| `tickets` | 3 | `id`, `type`, `requester`, `subject`, `sku`, `size`, `qty`, `lease_id`, `invoice_id`, `status`, `notes`, `created_at` | The work queue. Each open ticket is a job for the boss to route, and its `sku`/`lease_id`/`invoice_id` fields point to the records the specialists need. |
| `inventory` | 10 | `sku`, `name`, `size`, `qty`, `location` (key: `sku` + `size`) | Inventory checks whether an order or bulk request can be filled from stock and where to pick it. |
| `pricing` | 4 | `sku`, `unit_cost`, `list_price` | Accounting and customer service use it to quote prices and to see how much margin a discount would use up. |
| `vendors` | 3 | `id`, `name`, `specialty`, `lead_days` | Inventory picks who can restock an item and how long it will take (`lead_days`). |
| `invoices` | 1 → 2 | `id`, `vendor_id` → `vendors.id`, `amount`, `due_date`, `status`, `description` | Accounting sees which vendor bills are open or overdue and must be paid. |
| `leases` | 1 | `id`, `space_name`, `landlord`, `monthly_rent`, `next_due`, `notes` | Facilities knows what rent is owed, to whom, and when. |
| `cash_accounts` | 1 | `name`, `balance`, `date` | Accounting checks whether there's enough cash before paying anything. Checking went from $3,400.00 to $736.00 in the P9 run. |
| `payments` | 0 → 2 | `id`, `kind`, `ref_id`, `amount`, `account`, `paid_at`, `approved_by` | The record of money paid out. It starts empty, and `approved_by` records the human approval for each payment. |
| `desk` | 1 | `date_today`, `notes` | Sets the shop's "today" so every agent uses the same date for due-date math. |

### How the tables join

```
tickets.sku + tickets.size ──► inventory.sku + inventory.size
tickets.sku               ──► pricing.sku
tickets.invoice_id        ──► invoices.id ──► vendors.id (invoices.vendor_id)
tickets.lease_id          ──► leases.id
payments.kind + ref_id    ──► invoices.id or leases.id (no FK; meaning depends on kind)
payments.account          ──► cash_accounts.name
```

Neither `inventory` nor `pricing` has a foreign key, so they join on `sku`. There is no customers or orders table, so a ticket's `requester` is the only record of who the customer is.

---

## 2. The three open tickets

All three tickets are `status = open` and were created on 2026-08-31.

### Ticket 101: `customer_order` — Tauhid Zaman, "Bulldog tee"

- **Asks for:** 1 × `CC-TEE-WHITE`, size **S**.
- **Links:**
  - `inventory` (CC-TEE-WHITE, S): **qty 0**, Aisle B, so the item is out of stock.
  - `pricing` (CC-TEE-WHITE): list $28.00, cost $8.00.
  - `invoice_id 501` → `invoices`: **$840.00** to vendor 1 for "Rush reprint CC-TEE-WHITE S". Due **2026-08-28**, status `open`, so it is **3 days overdue**.
  - `vendors` 1: Bulldog Print Co, apparel reprint, 5 lead days.
- **What it means:** the order can't ship from stock. A restock was already ordered, but the bill for it is unpaid and past due. Filling this order means checking the invoice, paying it (with approval), and telling the customer when to expect the tee.
- **Likely agents:** Customer service (customer reply), Inventory (stock and reprint), Accounting (invoice 501).

### Ticket 102: `rent_notice` — Elm City Properties, "Rent due"

- **Asks for:** rent payment ("shop rent due in 2 days").
- **Links:**
  - `lease_id 1` → `leases`: Chapel Street shop, landlord Elm City Properties, **$2,400.00/month**, next due **2026-09-02**, which is 2 days after the desk date and matches the email.
  - `cash_accounts` checking: **$3,400.00**.
- **What it means:** rent is affordable, but cash is tight. Paying both rent ($2,400) and invoice 501 ($840) totals **$3,240**, which leaves **$160** in checking.
- **Likely agents:** Facilities (lease), Accounting (cash check and payment). A human approves the payment, which is recorded in `payments` with `approved_by`.

### Ticket 103: `price_override` — Yale AI Club, "Bulk hoodie discount"

- **Asks for:** 20 × `CC-HOOD-NAVY`, size **M**, at a bulk discount.
- **Links:**
  - `inventory` (CC-HOOD-NAVY, M): **qty 8**, Aisle A, so the shop is **12 short**. Other sizes on hand: S 4, L 14, XL 6.
  - `pricing` (CC-HOOD-NAVY): list $58.00, cost $22.00. At list price, 20 hoodies = **$1,160** revenue and $440 cost, so the margin is $36 per hoodie (62%).
  - `vendors` 1: Bulldog Print Co can reprint apparel in 5 days.
- **What it means:** this needs a discount decision (how much margin to give up) and a stock plan (8 now and 12 reprinted, or wait and ship all 20). A price override should go to a human for approval.
- **Likely agents:** Customer service (club reply), Accounting (discount and margin), Inventory (stock and reprint). The Boss signs off or sends it to a human.

### Links across tickets

- **Cash ties all three together.** Rent, the overdue invoice, and any reprint for the hoodie order all draw on the same $3,400 checking balance. Agents need to share that view, not approve payments one at a time.
- **Bulldog Print Co appears twice.** It is owed $840 (invoice 501, overdue) and would also be the vendor for a hoodie reprint for ticket 103. The overdue bill could hold up new work from them.
- **Every ticket needs other agents.** No ticket can be closed by a single specialist, which is why the team is fully connected.

---

## 3. MCP tools

Server: `mcp_server/server.py` (FastMCP, server name `campus-customs`). It works on `data/campus_customs_new.db` and is the agents' only way to reach shop data. Each tool returns only stored values (or values worked out from them, like margin and days overdue), or `found: false` if no row exists. Problems 3–4 added the first three tools. Problem 5 added nine more so the team can work all three open tickets.

### Problem 3 tools, by ticket

| Tool | Table it reads | Ticket it unlocks | Why it's the right tool for that ticket |
| --- | --- | --- | --- |
| `check_stock(sku, size?)` | `inventory` | **101**: Tauhid Zaman's tee order | Ticket 101 asks for `CC-TEE-WHITE` in size `S`. `check_stock("CC-TEE-WHITE", "S")` returns **qty 0 in Aisle B**, which shows the order can't ship from the shelf and has to wait on the rush reprint in invoice 501. |
| `get_lease(lease_id)` | `leases` | **102**: Elm City Properties rent notice | Ticket 102 only says "rent due in 2 days" and carries `lease_id 1`. `get_lease(1)` turns that into the facts needed to pay it: **$2,400 to Elm City Properties for the Chapel Street shop, due 2026-09-02**. |
| `get_pricing(sku)` | `pricing` | **103**: Yale AI Club bulk hoodie discount | Ticket 103 is a `price_override` for 20 `CC-HOOD-NAVY` hoodies. `get_pricing("CC-HOOD-NAVY")` returns **list $58, cost $22, margin $36 per hoodie**, so any discount can be checked against what the shop actually earns. |

**Tested** through a FastMCP client over stdio: each ticket's lookup returns the values above, and an unknown lease id or SKU returns `found: false`. Both `.db` files kept the same checksum, so nothing was written.

**Smoke test from the vibe coder (Problem 4):** with `campus-customs` connected through `.mcp.json`, the vibe coder called each tool on its ticket. Every output matched `campus_customs_new.db` when checked with sqlite3. The full evidence is in `output/mcp_smoke.json`.

| Ticket | Tool call | Tool output | Database value | Match |
| --- | --- | --- | --- | --- |
| 101 | `check_stock("CC-TEE-WHITE", "S")` | Classic Bulldog Tee, S, qty 0, Aisle B | `inventory`: qty 0, Aisle B | ✅ |
| 102 | `get_lease(1)` | Chapel Street shop, Elm City Properties, rent 2400, due 2026-09-02, notes null | `leases`: 2400.0, 2026-09-02, notes NULL | ✅ |
| 103 | `get_pricing("CC-HOOD-NAVY")` | cost 22, list 58, margin 36 | `pricing`: 22.0, 58.0 (58 − 22 = 36) | ✅ |

The only differences are formatting: SQLite stores REAL values such as `2400.0`, and the tool returns them as JSON numbers such as `2400`. `unit_margin` is computed by the tool and isn't a stored column.

### Every MCP tool (Problem 5)

| Tool | Table(s) it uses | Read / write | Added | Agents that get it |
| --- | --- | --- | --- | --- |
| `check_stock(sku, size?)` | `inventory` | read | P3 | inventory, customer_service |
| `get_lease(lease_id)` | `leases` | read | P3 | facilities, accounting |
| `get_pricing(sku)` | `pricing` | read | P3 | accounting, inventory, customer_service |
| `get_shop_date()` | `desk` | read | P5 | all five |
| `list_tickets(status?)` | `tickets` | read | P5 | boss, accounting |
| `get_ticket(ticket_id)` | `tickets` | read | P5 | all five |
| `get_invoice(invoice_id)` | `invoices` joined to `vendors` (+ `desk` for days overdue) | read | P5 | accounting |
| `list_vendors(specialty?)` | `vendors` | read | P5 | inventory, accounting, customer_service |
| `get_cash_balance(account?)` | `cash_accounts` | read | P5 | boss, accounting, facilities |
| `list_payments(kind?, ref_id?)` | `payments` | read | P5 | accounting, facilities |
| `update_ticket(ticket_id, status, note)` | `tickets` | **write**: status + appended, date-stamped note | P5 | boss only |
| `record_payment(kind, ref_id, approved_by, account?)` | `payments`, `cash_accounts`, `invoices` / `leases` (+ `desk`) | **write**: money out | P5 | **no agent**. Human approval path only (`POST /api/approve`, `team.py --approve`). |
| `record_purchase(vendor_id, sku, size, qty, approved_by, account?)` | `invoices` (new paid row), `payments`, `cash_accounts`, reads `vendors`/`inventory`/`pricing` (+ `desk`) | **write**: money out | P7 | **no agent**. Human approval path only (`POST /api/approve`). Cost = qty × `unit_cost`, and stock doesn't change until the goods arrive. |

How the new tools close the Problem 3 gaps:

- **Ticket 101:** `get_invoice(501)` shows the $840 rush reprint bill to Bulldog Print Co, 3 days overdue. `list_vendors` gives the 5-day lead time.
- **Ticket 102:** `get_cash_balance` shows $3,400 in checking. `list_payments(kind="rent", ref_id=1)` checks that rent wasn't already paid.
- **Ticket 103:** `check_stock("CC-HOOD-NAVY")` (all sizes) plus `get_pricing` and `list_vendors` cover the shortfall, margin, and reprint timing.
- **All tickets:** `get_ticket`/`list_tickets` read the queue, `get_shop_date` fixes "today", and `update_ticket` lets the boss record progress.

`record_payment` takes no amount. It reads the amount from the invoice or lease, refuses a blank or agent-name approver, refuses to pay twice, and refuses to overdraw. After paying it marks the invoice `paid`, or moves the lease's `next_due` forward a month. All 12 tools were tested over an MCP client on a throwaway copy of the database. The real `.db` files kept their checksum (`f447ca6a…`).

---

## 4. The five agents (Problem 5)

PydanticAI agents in `backend/`, all on **`gpt-6-luna`** through Portkey (`PORTKEY_API_KEY`). The model is set once in `backend/config.py` (`OPENAI_MODEL`, default `gpt-6-luna`). Prompts are in `backend/prompts/<agent>.md`, data types in `backend/models.py`, and each agent's tool list in `backend/agents/<agent>.py`.

| Agent | File / prompt | Job | MCP tools | Output |
| --- | --- | --- | --- | --- |
| Boss | `agents/boss.py`, `prompts/boss.md` | Reads the ticket, marks it `in_progress`, routes it to specialists, checks their sources, sets the final status, writes the resolution | `get_ticket`, `list_tickets`, `get_shop_date`, `get_cash_balance`, `update_ticket` | `TicketResolution` (an `AgentReport` when another agent asks it something) |
| Inventory | `agents/inventory.py`, `prompts/inventory.md` | Stock by size and aisle, shortfalls, other sizes, reprint vendor and ready date | `check_stock`, `get_pricing`, `list_vendors`, `get_ticket`, `get_shop_date` | `AgentReport` |
| Accounting | `agents/accounting.py`, `prompts/accounting.md` | Bills, days overdue, cash plan across tickets, double-pay check, margin and discount limits | `get_invoice`, `get_cash_balance`, `list_payments`, `get_pricing`, `get_lease`, `list_vendors`, `get_ticket`, `list_tickets`, `get_shop_date` | `AgentReport` |
| Facilities | `agents/facilities.py`, `prompts/facilities.md` | Lease and rent: amount, landlord match, due date, already paid?, landlord reply | `get_lease`, `list_payments`, `get_cash_balance`, `get_ticket`, `get_shop_date` | `AgentReport` |
| Customer service | `agents/customer_service.py`, `prompts/customer_service.md` | Honest reply drafts for customers, with options backed by stock data and no internal numbers | `get_ticket`, `check_stock`, `get_pricing`, `list_vendors`, `get_shop_date` | `AgentReport` (the reply draft is in `answer`) |

**Full connectivity.** Every agent also has a `delegate(to, task)` tool that can reach any of the other four. A delegated agent runs its own loop and returns an `AgentReport` to the caller. `backend/agents/base.py` holds the shared loop.

**The agent loop** (`run_agent`) drives each agent with `Agent.iter`: user prompt → model response (tool calls) → tool results → … → structured final output. The boss starts every ticket (`backend/team.py --ticket N` or `--all`, oldest first).

**Audit trail.** Every loop step appends one row to `output/audit_trail.json`, and nothing is ever wiped. Each row records the time, `run_id`, ticket, agent, `agent_run_id`, parent, the delegation chain and depth, the step number and kind (`run_start`, `user_prompt`, `model_request`, `model_response`, `tool_results`, `delegation`, `final`, `error`, `run_end`), the model, text and any reasoning summary, tool calls with arguments, tool results (trimmed to 1,500 characters), the final output, that step's token usage, and the running token total for the ticket. Refused delegations are logged with the reason. Human payments made with `--approve` are logged as agent `human`. Writes are atomic (temp file + rename). If the file is unreadable it is renamed aside, never deleted.

**Tested:** first with a scripted fake model on a throwaway database (P5, P7, P8). Then for real with `gpt-6-luna` on all three tickets in Problem 9 (section 8): all five agents took part, and the loop guard refused 3 loop-back delegations.

---

## 5. Safety

### Guardrails for real customers and real money

- **A human approves all money out.** No agent has `record_payment` or `record_purchase`. Paying needs a named person (`POST /api/approve` or `team.py --approve … --by NAME`), and the server rejects blank or agent-name approvers.
- **The server enforces the money rules, not the prompts.** Amounts come from the invoice or lease (no caller-supplied amounts). The server blocks double payment and overdrafts. Every payment row stores `approved_by`.
- **Least privilege.** Each agent gets only the MCP tools its job needs. Only the boss can change ticket status, and nobody can change stock, prices, or invoices.
- **Discounts, reprint orders, and customer or landlord messages are approval requests**, not actions. Customer replies are drafts. Discounts must stay above cost, at most 20% off for bulk, with margin of at least 40% of the discounted price.
- **Facts only from tools.** Prompts require every number to name its tool. Gaps go to `open_questions` instead of guesses. "Today" is the desk date.
- **Cash cushion and priority.** Accounting flags any plan that leaves checking under $500. Paying rent and invoice 501 together would leave $160, so a human must see that before approving both.
- **Fraud check on rent.** Facilities confirms that the landlord, amount, and due date match the lease before recommending payment, and sends anything odd (new bank details, new fees) to the boss and a human.
- **Privacy.** Customer service never shares cost, margin, cash, vendor debts, or other customers' details, and never asks for payment details.
- **Everything is auditable.** Every step, tool call, delegation (including refusals), approval and reset is in the append-only audit trail (`output/audit_trail.json`, which is never wiped).
- **One thing at a time.** The backend lock means a run, an approval and a reset can never overlap, so cash can't change underneath an agent mid-run.
- **"Resolved" never hides open decisions.** When a run finishes the ticket is marked `resolved`, but the boss's own status (`needs_approval`) is kept in the ticket note, and every waiting approval stays on the dashboard until a person acts.
- **People sign, by name, for an exact amount.** Approve buttons show the dollar amount, are disabled until **Signing as** is filled in, and reprint details can be checked before buying. Discounts and messages have no money button at all.

### Limits that keep token use in check (`backend/config.py`)

| Limit | Value |
| --- | --- |
| Model | `gpt-6-luna` for every agent (cheaper tier), set in one place via `OPENAI_MODEL` |
| Token budget per ticket, all agents combined | 200,000 tokens. New delegations are refused once it's spent, and each agent's limit is whatever is left. |
| Model calls per agent loop | Boss 12, each specialist 8 |
| Tool calls per agent loop | 16 |
| Max output tokens per model response | 8,000 |
| Delegation depth | 3 (boss → A → B → C) |
| Delegations per ticket | 8 |
| No loops | An agent can't delegate to itself or to anyone already in its chain |
| Audit row size | Tool results trimmed to 1,500 characters |
| Ticket runs | One ticket at a time, so later cash decisions see earlier ones |
| Actual use (P9) | 66,551 / 69,652 / 102,351 tokens for tickets 101 / 102 / 103, all under the 200k budget |

**Still to add before going live:** login so `approved_by` is a verified person rather than a typed name, a dollar cost cap per day through Portkey, and removing `unit_cost` from what customer service can see (today only its prompt stops it from repeating cost).

---

## 6. Backend routes (Problem 7)

FastAPI app in `backend/main.py`. Start it from `hw5/backend` with `uvicorn main:app --reload --port 8000`. Shop data goes through the MCP tools. CORS allows the Vite dashboard origins `http://localhost:5173` and `http://127.0.0.1:5173`. The dashboard (`frontend/`, `npm run dev`) is described in `output/design.md`.

- `GET /api/health`: model name, whether the Portkey key is set, which database is in use, and whether a run is in progress.
- `GET /api/tickets`: every ticket with its exact `status` and a simple `state` of `open` or `resolved` (via `list_tickets`).
- `POST /api/tickets/{ticket_id}/run`: runs the agent team on one ticket and returns the boss's `TicketResolution`, all delegations, and token usage (404 for an unknown id). When the run finishes, the ticket is marked `resolved`, and the boss's status and any waiting approvals go in the note (added in P8).
- `GET /api/tickets/{ticket_id}/summary`: the latest run on a ticket since the last reset, with the boss's resolution, each approval and whether a human has approved it, and a short per-agent summary of tasks, tools, hand-offs and answer (added in P8).
- `GET /api/events?limit=&ticket_id=&run_id=&since=`: recent agent events from `output/audit_trail.json`, showing what each agent said and which tools it used, for the board to poll.
- `POST /api/approve`: a human's Approve click, and the only route that moves money. `action: "payment"` (`kind` invoice/rent + `ref_id`) calls `record_payment`, and `action: "purchase"` (`vendor_id`, `sku`, `size`, `qty`) calls `record_purchase`. Both need `approved_by` and are logged in the audit trail as agent `human`.
- `GET /api/cash`: current `checking` balance from `cash_accounts` (via `get_cash_balance`).
- `GET /api/payments`: money already paid out, newest first (via `list_payments`), for the dashboard ledger (added in P8).
- `POST /api/reset`: copies `data/campus_customs.db` over `campus_customs_new.db` for a fresh run and returns checksums before and after. The audit trail is kept, and a reset row is appended.

Only one run, approval, or reset can touch the database at a time. A second one gets `409 busy`.

**Tested** on throwaway copies of the database and audit file. Every route gave the expected answer. Approving invoice 501 took checking from $3,400 to $2,560, a second attempt was refused as already paid, and an agent-name approver was refused. A purchase of 12 × M hoodies cost $264 (balance $2,296). Reset restored $3,400 and the original checksum `f447ca6a…`. The run route was tested end-to-end with a scripted fake model (ticket 101 → `needs_approval`, with events per step). The real databases weren't touched.

---

## 7. Dashboard (Problem 8)

React 19 + Vite 8 + TypeScript in `frontend/`. Start it with `npm run dev`, which opens `http://localhost:5173`. It calls the backend at `VITE_API_URL` (default `http://127.0.0.1:8000`). Full design reasoning is in `output/design.md`.

| Area | What it shows | Routes it uses |
| --- | --- | --- |
| Top bar | Shop day, backend and model status, **Signing as** (becomes `approved_by`), **Reset shop** | `/api/health`, `/api/reset` |
| Ticket rail (left) | All tickets as paper stubs: open, "team working", or a green **RESOLVED** stamp | `/api/tickets` (every 4 s) |
| Roster | Five agent seats with colour, monogram and a live status ("Checking the shelves", "Waiting on Accounting", ✓ done) | `/api/events` |
| Live floor | Hand-offs (`Bo → In` + task), tool chips with plain-English verbs, folded tool results, report-backs, refused delegations. Indented by delegation depth | `POST /api/tickets/{id}/run`, `/api/events?ticket_id&since` (every 1 s) |
| Debrief | Boss's resolution, draft reply (not sent), open questions, one card per agent (asked by, steps, answer, tools, hand-offs), facts | `/api/tickets/{id}/summary` |
| Till (right) | Checking balance that counts down on payment, with a −$ chip and a $500 cushion bar; **Waiting on you** approvals with exact-amount Approve buttons; **Paid out** ledger | `/api/cash`, `/api/approve`, `/api/payments` |

Payments and purchases happen only when a person clicks Approve with a name entered. Discounts and customer messages show up as decisions with no money button.

---

## 8. Problem 9: full run on the three tickets

Reset the working database (`POST /api/reset`, 2026-10-31 18:51:42 UTC). Starting checking was **$3,400.00**. Each ticket was run from the React board with `gpt-6-luna`, and the human approvals were signed on the board by Natalie Sheppard. Details are in `output/desk_tickets.html` (Actual and Cash tabs), `output/resolved_tickets.json`, and `output/resolved_board.html` (board screenshots), and every step is in `output/audit_trail.json`.

| Ticket | Run | Boss called first | Agents | Tokens | Approvals asked → decided | Cash |
| --- | --- | --- | --- | --- | --- | --- |
| 101 Bulldog tee | `run-d96db0602b` | inventory (+ customer service in parallel) | boss, inventory, customer service, accounting | 66,551 | invoice 501 $840 → **not approved**; customer message → pending | $0.00 |
| 102 Rent due | `run-3f6e29ed6a` | facilities (+ accounting in parallel) | boss, facilities, accounting | 69,652 | rent lease 1 $2,400 → **approved** | −$2,400.00 |
| 103 Bulk hoodies | `run-da700952be` | accounting (+ inventory in parallel) | boss, accounting, inventory, customer service | 102,351 | reprint 12 × M $264 → **approved**; discount $928 and message → pending | −$264.00 |

- **Ending checking: $736.00.** This matches `cash_accounts` in `campus_customs_new.db` ($3,400 − $2,400 − $264). Payments #1 (rent) and #2 (invoice 502, the reprint) are both `approved_by` Natalie Sheppard. Invoice 501 ($840) is still open.
- The boss ended every ticket at `needs_approval`, and the desk marked each one `resolved` when its run ended.
- The guardrails held: no agent called `record_payment` or `record_purchase`, 3 loop-back delegations were refused, and every ticket stayed well under the 200k-token budget (238,554 tokens in total).
- Compared with the Problem 6 plan: first calls matched for 101 and 102. 103 went to accounting first, not customer service, because that's how `boss.md` routes `price_override`. `get_pricing` was predicted for 101 but not used.

---

## 9. Notes for later problems

- Agents write to `campus_customs_new.db` only.
- Use `desk.date_today` (2026-08-31) as "today".
- Payments need a human approver (`payments.approved_by` is NOT NULL).
- Ticket `status` values: `open`, `in_progress`, `needs_approval`, `waiting_on_vendor`, `resolved` (enforced by `update_ticket`). Invoice `status` values: `open`, and `paid` after `record_payment`.
- Run the team from `hw5/`: `.venv/bin/python backend/team.py --ticket 101` or `--all`. A run writes ticket status and notes to `campus_customs_new.db`.
