# AI Prompts Log — HW5

Living log of what we typed into the vibe coder while completing this homework. One section per problem, updated as we go.

Each section has:
- **Problem number and title**
- **Prompt typed**: the first prompt for the problem
- **What was lacking**: one sentence on what the first prompt was missing (or N/A)
- **Follow-up prompts typed**: any follow-ups, in order
- **Evidence of work**: what the AI produced

Runtime LLM prompts live in `backend/prompts/`; script outputs land in `output/`; local data goes in `data/`.

---

## Problem 1 — Vibe coder prompts

**Prompt typed:**
> hi we are starting HW5.  can you setup a folder and everything we will need?

**What was lacking:**
The first prompt didn't name the project folder or give any HW5 context, so the AI started in an empty workspace and set up a generic folder until the follow-ups pointed it at `AI Foundations` and described the project.

**Follow-up prompts typed:**

1. > Yes, move this session to /Users/natalie/Desktop/AI Foundations and set up HW5 there, matching how the earlier HWs are organized.

2. > we will need to stick to gpt-5.6-luna for this hw

3. > ok here's the context for this hw.  we are going to be creating a campus customs multi agent operations - an agentic team that runs the shop.  When an open ticket lands on a board (customer orders, rent, unpaid bills, discount requests, or anyhting the shop handles).  There will be an MCP server, a fastAPI backend with a multi agent team and a react dashboard so a human can watch the agents at work and approve requests.  the agent team has full connectivity - so any agent can delegate a task to any other. agent for help.  These will be the agets we build - boss, inventory, accounting, facilities and customer service

4. > Problem 1: Vibe coder prompts.  we need to create the ai_prompts.md and keep it updated.  this is the log of what we typed in the vibe coder.  similar to the past, one section for each problem and each section needs to include the problem number and titile, prompts, and any follow-up prompts (including one sentence on what was lacking after the first prompt)

**Evidence of work:**
- Created branch `hw5` and `hw5/` with `prompts/`, `output/`, `data/`, `.gitignore`, `.env.example`, `requirements.txt`, `README.md`, a working `.venv`, and this `AI_prompts.md`, mirroring the HW4 layout.
- Added a Model section to `README.md`: all HW5 AI calls use `gpt-5.6-luna` via `OPENAI_MODEL`.
- Added the project overview to `README.md`: the ticket board, the MCP server / FastAPI backend / React dashboard, and the five fully connected agents (boss, inventory, accounting, facilities, customer service).
- Set this log's format and titled this section "Vibe coder prompts". A new section will be added for each problem as we work.

---

## Problem 2 — Study the Campus Customs database

**Prompt typed:**
> problem 2: Study the campus customs database.  We need to open data/campus_customs.db and look through every table and its fields.  copy the original file to data/campus_customs_new.db - as later problems update that working copy.  We need to study the three open tickets to see how they link to other tables.  also start output/harness.md.  for each table, list the fields and one short line on why that table matters for the agents.

**What was lacking:**
N/A — the prompt named the file, the working copy, the tickets to trace, and what harness.md should hold, so the work was done in one pass.

**Follow-up prompts typed:**
None.

**Evidence of work:**
- Copied `data/campus_customs.db` → `data/campus_customs_new.db` (same checksum, original untouched).
- Read all 9 tables (`tickets`, `inventory`, `pricing`, `vendors`, `invoices`, `leases`, `cash_accounts`, `payments`, `desk`).
- Started `output/harness.md`: each table's fields and one line on why it matters to the agents, how the tables join, and how each open ticket (101 tee order, 102 rent, 103 bulk hoodie discount) links to inventory, pricing, invoices, vendors, leases, and cash.
- Added `data/*.db` to `hw5/.gitignore` so the database isn't pushed to GitHub, the same as HW4.

---

## Problem 3 — Build the MCP server

**Prompt typed:**
> Problem 3: Build the MCP server.  We need to write an MCP server in mcp_server/ usingfastMCP.  It will talk to data/campus_customs_new.db.  Every agent in thei HW will ues the tools in the mcp server.  we'll add more tools later, but will start with three tools that we know we will need for the tickets in the database.  we need to keep the names clear and never invent any data, only use what is in the database.  in output/harness.md, list each of the three MCP tools.  for every tool, include which table it reads, which ticket it unlocks (101, 102, 103) and one sentence on why that tools is the right one for that ticket.  It cannot be a vague answer like "reads inventory" - it must tie the tool to the ticket.  Add a short mcp_server/readme.md file that explains what the mcp server is for, which database file it uses and the three tools it has.

**What was lacking:**
The prompt didn't say which Python version to use, and the HW5 environment had been built on macOS's Python 3.9, which can't install FastMCP, so the AI rebuilt `.venv` on Python 3.12.

**Follow-up prompts typed:**
None.

**Evidence of work:**
- `mcp_server/server.py`: FastMCP server `campus-customs` with `check_stock` (inventory → ticket 101), `get_lease` (leases → ticket 102), and `get_pricing` (pricing → ticket 103). It opens `data/campus_customs_new.db` read-only and returns `found: false` instead of inventing data.
- `mcp_server/README.md`: purpose, database file, the three tools, and how to run it.
- `output/harness.md`: new MCP tools section with the table, ticket, and a ticket-specific reason for each tool.
- Added `fastmcp` to `requirements.txt` and rebuilt `.venv` on Python 3.12. Tested every tool through a FastMCP client: the ticket lookups return the real values, unknown ids return not found, and the database checksums didn't change.

---

## Problem 4 — Add the MCP server to the vibe coder and test each tool

**Prompt typed:**
> problem 4: add the MCP server to vibe coder and test each tool.  now in this vibe coder, we need to add our MCP server to this project so the vibe coder can call the tools,  save the connection JSON text in .mcp.json at the project root.  once connected, test each of the three mcp tools.  save evidence in output/mcp_smole.json.  For every tool, we need to include: the prompt you asked the vibe coder, the tool name, the tool output (which mus match values in data/campus_customs_new.db)

**What was lacking:**
The prompt didn't account for the vibe coder only loading `.mcp.json` servers when a session starts, so after the config was saved the session had to be restarted before the tools could be called.

**Follow-up prompts typed:**
> I restarted and approved the campus-customs MCP server. Go ahead and test each of the three tools and save output/mcp_smoke.json.

> HW5 Problem 4 (continuing from another session). The campus-customs MCP server is already in .mcp.json at the AI Foundations root and in hw5/.mcp.json; the server is hw5/mcp_server/server.py and reads hw5/data/campus_customs_new.db. Using the campus-customs MCP tools (not a script), test each tool on its ticket: check_stock("CC-TEE-WHITE","S") for ticket 101, get_lease(1) for ticket 102, get_pricing("CC-HOOD-NAVY") for ticket 103. Check each output against hw5/data/campus_customs_new.db with sqlite3. Save hw5/output/mcp_smoke.json with, for every tool: the prompt asked, the tool name, the tool output, and the matching database values. Then add the smoke-test results to the MCP tools section of hw5/output/harness.md, and finish the Problem 4 section of hw5/AI_prompts.md (replace the "in progress" placeholders; add the follow-ups: "I restarted and approved the campus-customs MCP server. Go ahead and test each of the three tools and save output/mcp_smoke.json." and this pasted prompt). Stay on branch hw5.

**Evidence of work:**
- Added `campus-customs` to `.mcp.json` at the `AI Foundations` root (where the vibe coder runs), next to the existing `yale-som-courses` server, and saved the same connection text in `hw5/.mcp.json`.
- Confirmed the connection JSON launches the server and lists `check_stock`, `get_lease`, `get_pricing`.
- The vibe coder called all three tools through the MCP connection: `check_stock("CC-TEE-WHITE","S")` (ticket 101) returned qty 0 in Aisle B, `get_lease(1)` (ticket 102) returned $2,400 to Elm City Properties due 2026-09-02, and `get_pricing("CC-HOOD-NAVY")` (ticket 103) returned cost $22, list $58, margin $36.
- Checked each output against `data/campus_customs_new.db` with sqlite3. All three match.
- Saved the evidence in `output/mcp_smoke.json` (prompt, tool name, tool output, and database values for each tool) and added a smoke-test table to the MCP tools section of `output/harness.md`.
- The tools only became available once the session was running in the `AI Foundations` folder, because project MCP servers load from that folder's `.mcp.json`.

---

## Problem 5 — Build the agent team and grow the MCP tools

**Prompt typed:**
> Problem 5: build the agent team and grow the MCP tools.  now we are going to buld the agentic team for campus customs using pydanticAI: Boss, Inventory, Accounting, Facilities and Customer Service.  Include prompts, models, and agent loops so they can delegate work to each other with full connectivity.  Put the agent prompts in backend/prompts/ - one file per agent.  Put the data types in backend/models.py, and the agent files under backend/.  Use portkey_API_key and only gpt-6-luna for every agent.  Write each prompt in your own words with the shop rules that the agent needs.  more detailed prompts that cover all aspects of an agent's work and scope will score higher.  Then add any tools the agent needs to the MCP server so they can work on open tickets.  the shop facts come from the mcp server over data/campus_customs_new.db - do not invent a second shop-tools layer that bypasses the MCP.  wire the agents so they append to output/audit_trail.json as the run - for each agent loop step, record enough to audit later. append to this file and do not wipe it after each run.  In output/harness.md, list each agent and each MCP tools (including additional ones added in this problem) along with which table the tool uses.  alsoo add a short safety section - the guardrails a real business would want when agents touch real customers and real money, plus limits that keep token use in check.  Update mcp_server/readme.md wo the tool list matches what we have now.

**What was lacking:**
The prompt didn't say whether agents may move money or change records, so the vibe coder had to decide that payments go through a human-only `record_payment` path, and that only the boss may update ticket status.

**Follow-up prompts typed:**
_(none yet)_

**Evidence of work:**
- **MCP server** (`mcp_server/server.py`): added 9 tools, for 12 in total. The new read tools are `get_shop_date`, `list_tickets`, `get_ticket`, `get_invoice`, `list_vendors`, `get_cash_balance`, and `list_payments`. The new write tools are `update_ticket` (boss only) and `record_payment` (human only: amount read from the database, no double payment, no overdraft, named approver). All 12 were tested over an MCP client on a throwaway database copy, and the real `.db` checksums didn't change.
- **Agents** (`backend/agents/`): boss, inventory, accounting, facilities, and customer_service, each with its own MCP tool allowlist and a `delegate(to, task)` tool that reaches any other agent. `base.py` has the shared `Agent.iter` loop, plus delegation limits (depth 3, 8 per ticket, no loop-backs) and token limits.
- **Prompts** (`backend/prompts/*.md`): one detailed prompt per agent covering its job, tools, step-by-step process, shop rules (desk date, human approval for money, discount limits, $500 cash cushion, no double payment, no internal numbers to customers), delegation, and output format.
- **Data types** (`backend/models.py`): `AgentReport`, `TicketResolution`, `ApprovalRequest`, `Delegation`, `AuditStep`, and `TicketRunResult`.
- **Model**: `gpt-6-luna` through Portkey, fixed in `backend/config.py`. One live call confirmed it works.
- **Audit trail**: every loop step (prompt, model response, tool calls, tool results, delegations including refusals, final output, errors, and token usage) is appended to `output/audit_trail.json`. A scripted no-API test showed the file growing from 32 to 64 rows across two runs.
- **Docs**: `output/harness.md` now has the full tool and table list, the agent table, and a safety section with limits. `mcp_server/README.md` lists all 12 tools.
- A full live run of the team on tickets 101–103 hasn't been done yet.


---

## Problem 6 — Plan the three tickets

**Prompt typed:**
> Problem 6: Plan the three tickets.  Before we wire the backend, we need to write down what we expect the team to do on each open ticket.  build output/desk_tickets.html - a page we can doubleclick with one tab per ticket.  Add empty cash and reflection tabs for later problems (these can stay blank for now).  On each ticket tabe, fill in an expected section only and leave room for an actual section that we will fill in after we run the agents.  for each ticket in the expected section, we need to write - who the boss should call first and why, all the agent delegations we expect, and which mcp tools we expect to run.  ticket 101 - i think will go to inventory first and use check stock, get pricing, list payment; ticket 102 i think will call facilities first and use  get lease, get cash balance, update ticket status, record payment ; ticket 103 i think will call customer service first and use check stock, get pricing

**What was lacking:**
The ticket 102 prediction included `record_payment`, which no agent can call (it is human-only from Problem 5). The page lists it as "not expected during the agent run" and explains the human approval step instead.

**Follow-up prompts typed:**
_(none yet)_

**Evidence of work:**
- Built `output/desk_tickets.html`, a self-contained page with no external files that opens with a double-click. It has five tabs: Ticket 101, Ticket 102, Ticket 103, Cash (blank), and Reflection (blank).
- Each ticket tab has a fact strip, an **Expected** section (who the boss calls first and why, a table of expected delegations with what each agent should return, a table of expected MCP tools with who calls them and why, and the expected final status and approvals), and an empty **Actual** section to fill in after the run.
- Our predictions are tagged "your prediction". Other tools the agent prompts require (`get_ticket`, `get_shop_date`, `update_ticket`, `get_invoice`, `list_vendors`, `list_payments`) were added to the tables with the reason for each.
- Ticket 103 keeps the prediction that customer service goes first, with a note that `backend/prompts/boss.md` routes `price_override` to accounting first, so the actual run may differ.

---

## Problem 7 — Backend routes

**Prompt typed:**
> Problem 7: backend routes.  The react front end dashboard needs a backend it can call.  in backend/main.py, use fastAPI and add routes that do the following: return the three tickets and whether each is open or resolved, take a ticket id and run your agent team on that ticket, return recent agent events - what each agent said and which tools they used - so the board can refresh, approve a payment or purchase after a human clicks approve (agents only prepare the pay; this route is what actually changes cash), return the current checking balance from cash_accounts, reset the database to the original values when you want to try a fresh run.  from the backend/ folder, start the server with: uvicorn main:app --reload --port 8000.  this turns on the backend so the frontend dashboard can call these routes.  in output/harness.md, list each route in one line (what url/what it does)

**What was lacking:**
The prompt asked for approving a "purchase", but no MCP tool could buy anything, so the vibe coder added a human-only `record_purchase` tool for reprint orders.

**Follow-up prompts typed:**
_(none yet)_

**Evidence of work:**
- `backend/main.py` (FastAPI) has 7 routes: `GET /api/health`, `GET /api/tickets`, `POST /api/tickets/{id}/run`, `GET /api/events`, `POST /api/approve`, `GET /api/cash`, and `POST /api/reset`. Each is listed in one line in `output/harness.md`, section 6.
- Added the MCP tool `record_purchase` (human-only, cost from `pricing`, writes a paid invoice and a payment, lowers cash). Request and response types were added to `backend/models.py`, and FastAPI and uvicorn to `requirements.txt`.
- Approvals and resets go through one lock, so they can't collide with an agent run. Every approval (including refused ones) and every reset is appended to the audit trail.
- Tested every route on throwaway copies: pay invoice 501 ($3,400 → $2,560), double payment refused, agent-name approver refused, purchase of 12 hoodies ($264), and reset back to $3,400 with the original checksum. The run route was tested with a scripted fake model. The real databases weren't touched.

---

## Problem 8 — Agent dashboard

**Prompt typed:**
> Problem 8: agent dashboard.  Now we will build the frontend dashboard in frontend/ with react + vite + typescript.  the page needs to call the routes that were built in problem 7.  at minimum the board should include - list of all three tickets, let us pick one ticket and start the agent team on it, show each agent and what they are saying / doing while the ticket runs, mark a ticket as  resolved when the run finishes, show a short summary of what each agent did on that ticket, let a human approve a pay or purchase when asked, show the checking balance (it should drop after an approved pay).  Make the dashboard look good.  we want it to be a simple and usable interface that a real person would want to sit at and use.  tell the front end to talk to the backend.  on the backend allow the vite page origin so the browser is allowed to call those routes.  start the board with: npm run dev.  This should open the react desk in browser so we can pick the tickets and watch the agents.  we need to wrtie to output/design.md with what we chose for the dashboard look (layout, how agents read differently, how resolved tickets and cash show up) and why - including the creative choices that make it feel special and like something that a human would want to use

**What was lacking:**
"Mark a ticket as resolved when the run finishes" conflicted with the Problem 5 rule that a ticket is resolved only once nothing is waiting on approval. The vibe coder marks it resolved when the run ends and keeps the boss's status and the waiting approvals visible on the board.

**Follow-up prompts typed:**
_(none yet)_

**Evidence of work:**
- `frontend/` (React 19 + Vite 8 + TypeScript): ticket rail, agent roster with live status, a live feed of hand-offs and tool calls polled every second, a debrief with the boss's resolution and a card per agent, a till with an animated checking balance, an approvals tray with named sign-off, and a paid-out ledger. `npm run dev` opens `http://localhost:5173`.
- Backend additions in `backend/main.py`: `GET /api/tickets/{id}/summary`, `GET /api/payments`, resolve-on-finish in the run route, and `running_ticket` in health. CORS already allows the Vite origin. Reprint approvals now carry `vendor_id`/`sku`/`size`/`qty` (`models.py` and three prompts), so the human can buy in one click.
- `output/design.md` explains the layout, agent identities, resolved stamp, cash display and creative choices.
- Tested in the browser against a throwaway database with a scripted fake model (no tokens): live feed and roster during the run, then the stamp, debrief and three approvals. Approving $840 counted checking down from $3,400 to $2,560 and added a ledger line. Reset restored $3,400. No console errors, and the real databases weren't touched.

---

## Problem 9 — Resolve the tickets

**Prompt typed:**
> problem 9: resolve the tickets.   ok before testing the agents on a full run over the three tickets, reset the working database data/campus_customs_new.db again so we can start clean.  note the starting checking balance, then run all three tickets on the board until each is resolved.  open output/desk_tickets.html from problem 6.  on each ticket tab we need to fill in the actual section based on this run - which agents worked, what they delegated, which tools they used.  keep the expected section so we can compare.  On the cash tab, we need to itemize the money - starting checking balance (after the reset), for each ticket how the cash changed when that ticket was resolved and why, ending checking balance which must match cash_accounts in the working database.  The wrong cash will lose pints.  Also we need to save output/resolved_tickets.json - for each ticket include id, final status, short outcome, what each agent contributed and any human approvals, output/resolved_board.html - a page that we can doubleclick with a screenshot of the react board for each resolved ticket.  we need to append real runs to output/audit_trail.json.  finish output/harness.md so it covers tables, mcp tools, the five agents, API routes, the dashboard and safety rules

**What was lacking:**
The prompt didn't say which money approvals the human should sign, and that decides the ending cash. The vibe coder ran all three tickets first and then asked. The answer was to approve rent ($2,400) and the hoodie reprint ($264) and hold invoice 501, signed as Natalie Sheppard.

**Follow-up prompts typed:**
> (answer to the vibe coder's question) Approve: Rent $2,400 (ticket 102), Reprint 12×M $264 (ticket 103). Signer: Natalie Sheppard.

**Evidence of work:**
- Reset the working database through `POST /api/reset` (checksum back to `f447ca6a…`). Starting checking was **$3,400.00**.
- Ran tickets 101, 102 and 103 from the React board with `gpt-6-luna` (`run-d96db0602b`, `run-3f6e29ed6a`, `run-da700952be`). All three ended `resolved`, using 238,554 tokens in total, and every step was appended to `output/audit_trail.json`.
- Approved on the board as Natalie Sheppard: rent, −$2,400.00 (payment #1), and the reprint of 12 × CC-HOOD-NAVY M, −$264.00 (invoice 502, payment #2). Invoice 501 ($840) was held.
- **Ending checking: $736.00**, which matches `cash_accounts` in `campus_customs_new.db`.
- `output/desk_tickets.html`: the Actual sections are filled in for all three tickets (first call, delegations including refused ones, tools per agent, result vs. expected), and the Cash tab itemizes the money. The Expected sections are unchanged.
- `output/resolved_tickets.json` (per ticket: id, final status, outcome, each agent's contribution and tools, approvals with the human decision, cash change) and `output/resolved_board.html` (a self-contained page with a board screenshot per resolved ticket; images also in `output/screenshots/`).
- `output/harness.md` is complete: tables, MCP tools, the five agents, safety rules, API routes, the dashboard (new section 7) and the Problem 9 run (new section 8).

---

## Problem 10 — Reflection

**Prompt typed:**
> Problem 10: reflection.  we need to open output/desk_tickets.html and fill in the reflection tab in my own vibe.  here are the questions and my thoughts on each ticket - how would you evaluate the performance of the agents on each ticket and why - the agents performed well across all.  It followoed our defined logic and required human approvas for actual payment.  For each ticket, how did the actual compare to the expected plan you wrote earlier?  for ticket 101 and 102, the expected first agent matched and the tools that were expected were used.  most different was that multiple agents could have been called in parallel.  For ticket 103, i predicted customer service would be called first (which is how it would be handled in a human world), but this actual ended up being later.  What would have been simpler as one agent with tools and why?  I think that the rent payment would have been simpler as a separate agent.  this is somewhat different from the actual business that campus customs runs, so seems that there should be standalone agent for operations outside of the core business.  Describe three new problems campus customs might face that this agent team could solve with the tools you built  - custom orders for t shirts for a specific event, bulk orders for specific colleges (i.e. school of management), or a multi product order from a customer.  Describe three new problems campus customs might face that this agent team could not solve with the tools we built - custom returns, product complaints and options to remediate them, renewing the lease.  these would require different customer service tools.

**What was lacking:**
N/A. The prompt gave an answer for every question. The only change was a note that `get_pricing` was the one expected tool not used on ticket 101.

**Follow-up prompts typed:**
_(none yet)_

**Evidence of work:**
- Filled in the Reflection tab of `output/desk_tickets.html` in first person, using my answers: an evaluation per ticket, actual vs. expected for 101/102 (first agent matched, parallel calls were the surprise) and 103 (customer service came last, not first), rent as a standalone agent outside the core business, three problems the team could solve (event tees, school bulk orders, multi-product orders), and three it couldn't (returns, complaints and fixes, lease renewal) because they need different customer service tools.

---

## Problem 11 — Submit to GitHub

**Prompt typed:**
> Problem 11: Submit to GitHub.  We need to push the code to a public github repository so the graders can clone it.  i need the repo url that i can submit on canvas and also put it in output/github_url.txt.  Do not push the real .env to the github repo.  We do need to include both database files under data/ so the graders can run the app easily.  Attached image is the expected layout.  REAMME should explain - copy original DB to the working copy when you need a clean run, start MCP server, start FastAPI backend, start the React board, reset the DB before a full three ticket run

**What was lacking:**
The prompt didn't name the repo. Following HW4 (`mtg408-hw4`), the vibe coder made a dedicated public repo, `mtg408-hw5`, containing only `hw5/`, so the private course repo stays private.

**Follow-up prompts typed:**
_(none yet)_

**Evidence of work:**
- Public repo: https://github.com/nps127/mtg408-hw5 (also in `output/github_url.txt`). It contains `hw5/` in the expected layout plus a short root README.
- Both databases are committed (`data/campus_customs.db` and `data/campus_customs_new.db`). `.gitignore` no longer excludes `data/*.db`.
- The real `.env` is not in the repo, and only `.env.example` with placeholders is. Before pushing, every file was scanned for the real Portkey key and common token patterns, with no hits. `.venv/`, `node_modules/`, and caches were excluded.
- `README.md` explains setup, copying the original DB to the working copy, starting the MCP server, the FastAPI backend and the React board, and resetting before a full three-ticket run.
- Smaller fixes to match the course `AGENTS.md`: the model is now read from `OPENAI_MODEL` (default `gpt-6-luna`), and `.mcp.json` uses relative paths so it works in a fresh clone.

