# HW5 — Campus Customs multi-agent operations

An agent team that runs the Campus Customs shop. When an open ticket lands on the board (a customer order, a rent notice, a discount request), five PydanticAI agents (Boss, Inventory, Accounting, Facilities, Customer Service) pick it up, delegate to each other, and look up every fact through the **campus-customs MCP server**. A person watches on a React dashboard and approves anything that moves money.

```
React board (frontend/, :5173)  ──HTTP──►  FastAPI (backend/main.py, :8000)
                                               │  agent team (backend/agents/)
                                               ▼
                                  campus-customs MCP server (mcp_server/server.py)
                                               │
                                               ▼
                                  data/campus_customs_new.db  (working copy)
```

## What's in this folder

| Path | Purpose |
| --- | --- |
| `data/campus_customs.db` | **Original** shop database. Never changed. |
| `data/campus_customs_new.db` | **Working copy.** Every run and approval writes here. As committed, it holds the state after the Problem 9 run (checking $736.00). |
| `mcp_server/` | FastMCP server with the 13 shop tools (see `mcp_server/README.md`) |
| `backend/main.py` | FastAPI routes the dashboard calls |
| `backend/models.py` | Data types (agent reports, ticket resolution, approvals, audit rows, API bodies) |
| `backend/prompts/` | One prompt per agent: `boss.md`, `inventory.md`, `accounting.md`, `facilities.md`, `customer_service.md` |
| `backend/agents/`, `team.py`, `config.py`, `shop_mcp.py`, `audit.py` | Agent loop and delegation, CLI runner, model and limits, MCP connection, audit trail |
| `frontend/` | React + Vite + TypeScript dashboard |
| `output/` | Homework deliverables: `harness.md`, `mcp_smoke.json`, `desk_tickets.html`, `design.md`, `resolved_tickets.json`, `resolved_board.html`, `audit_trail.json`, `github_url.txt` |
| `AI_prompts.md` | Log of the prompts used for each problem |

## 0. One-time setup

You need Python 3.10+ (FastMCP needs it, and macOS's built-in `python3` is 3.9), Node 20+, and a Portkey API key.

```bash
cd hw5
cp .env.example .env            # then put your key in .env: PORTKEY_API_KEY=...
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd frontend && npm install && cd ..
```

`.env` is git-ignored and never committed. Every agent uses `gpt-6-luna` through Portkey, set by `OPENAI_MODEL` in `.env` (default `gpt-6-luna`).

## 1. Copy the original database to the working copy (for a clean run)

The app only ever writes to `data/campus_customs_new.db`. To start from the original shop data (3 open tickets, $3,400 in checking, no payments), copy the original over it:

```bash
cd hw5
cp data/campus_customs.db data/campus_customs_new.db
```

If the backend is already running, the dashboard's **Reset shop** button (or `curl -X POST http://127.0.0.1:8000/api/reset`) does the same copy and logs it in the audit trail.

## 2. Start the MCP server

The tools live in `mcp_server/server.py` and read `data/campus_customs_new.db`.

```bash
cd hw5/mcp_server
../.venv/bin/python server.py           # stdio, for Claude Code or any MCP client
../.venv/bin/python server.py --http    # or HTTP at http://127.0.0.1:8001/mcp
```

- **Claude Code:** `hw5/.mcp.json` already registers it as `campus-customs`. Open Claude Code in `hw5/`, approve the server, and the tools appear (`check_stock`, `get_lease`, `get_pricing`, …).
- **The backend doesn't need a separate terminal.** `backend/shop_mcp.py` loads this same server in-process and talks to it over FastMCP's in-memory MCP transport. Agents still reach shop data only through MCP tools.

## 3. Start the FastAPI backend

```bash
cd hw5/backend
../.venv/bin/uvicorn main:app --reload --port 8000
```

Check it with `curl http://127.0.0.1:8000/api/health`, which should show `"portkey_key_set": true`. All routes are listed in `output/harness.md`, section 6.

## 4. Start the React board

In a second terminal:

```bash
cd hw5/frontend
npm run dev        # opens http://localhost:5173
```

The board calls the backend at `http://127.0.0.1:8000` (change it with `VITE_API_URL` in `frontend/.env`). The backend allows the Vite origin through CORS.

## 5. Reset the database before a full three-ticket run

Before running all three tickets, reset so the cash numbers start from $3,400.00. Use either option:

- click **Reset shop** in the board's top bar (recommended while the backend is running), or
- stop the backend and run `cp data/campus_customs.db data/campus_customs_new.db` (step 1).

Then on the board:

1. Type your name in **Signing as** (it becomes `approved_by` on any payment).
2. Pick ticket **#101** and click **Start the team**. Watch the live floor. When the run ends the ticket is stamped **Resolved** and the debrief opens.
3. Approve, or don't, anything under **Waiting on you**. Only these buttons move money, and the checking balance drops when you approve.
4. Repeat for **#102** and **#103**.

Every agent step, hand-off, tool call, approval and reset is appended to `output/audit_trail.json`. Nothing is ever wiped.

### Without the board (CLI)

```bash
cd hw5
.venv/bin/python backend/team.py --ticket 101        # one ticket
.venv/bin/python backend/team.py --all               # every open ticket
.venv/bin/python backend/team.py --approve rent 1 --by "Your Name"   # human approves a payment
```

## Safety, in one paragraph

No agent can pay anything: `record_payment` and `record_purchase` are human-only and called only from `POST /api/approve`. The server takes amounts from the database, refuses double payments, overdrafts, and approvers that are blank or agent names, and stores who approved. Each agent gets only the MCP tools its job needs. Delegation is capped (depth 3, 8 per ticket, no loop-backs), and each ticket has a 200k-token budget. Details are in `output/harness.md`, section 5.
