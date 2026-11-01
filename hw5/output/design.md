# Design — the Campus Customs desk

The dashboard (`frontend/`, React + Vite + TypeScript) is designed to feel like **the counter of a small campus shop**, not like an admin console. Someone sits down, picks a ticket off the rail, watches the team work it, and signs for anything that moves money. Every choice below supports that idea.

---

## Layout: three columns, read left to right like the work itself

```
┌──────────── top bar: crest · shop day · backend status · "Signing as ___" · Reset ────────────┐
│ TICKET RAIL      │ THE FLOOR                                          │ THE TILL                 │
│ paper stubs      │ ticket header + "Start the team"                   │ checking balance         │
│ #101 #102 #103   │ roster: five seats, live status                    │ "Waiting on you" tray    │
│                  │ [Live floor] [Debrief]                             │ "Paid out" ledger        │
│                  │ live feed of hand-offs and lookups / or debrief    │                          │
└──────────────────┴────────────────────────────────────────────────────┴──────────────────────────┘
```

- **Left, the ticket rail:** what's waiting. Tickets are always visible, so switching is one click.
- **Centre, the floor:** what's happening. It gets the most width because the agents' work is the show.
- **Right, the till:** money and decisions. It's kept apart on purpose: cash and the Approve buttons sit in their own column, never mixed into the agent chatter, so a person can't confuse "an agent suggested paying" with "money moved".
- The rail and the till are **sticky**, and the feed **scrolls inside its own panel**. During a run the roster and the cash balance stay in view while the transcript grows.
- Under 1,180 px the till drops below the floor as a row of cards, so it still works on a laptop.

**Why:** people read left to right as "inbox → work → outcome". Putting money last, in a fixed place, matches how a shop actually runs: the work happens, and the till is touched only on purpose.

---

## How the agents read differently

Each agent has an **identity**, a colour and a two-letter monogram, and keeps it everywhere: the roster seat, every feed line, hand-off arrows, and debrief cards.

| Agent | Colour | Monogram | Why that colour |
| --- | --- | --- | --- |
| Boss | Yale blue `#00356b` | **Bo** | The shop's own colour: the boss speaks for the shop |
| Inventory | Green `#2e7d4f` | **In** | Stock on the shelf, "go" |
| Accounting | Amber `#b26a00` | **Ac** | Ledger gold. Money deserves care, not alarm |
| Facilities | Brick `#a8452f` | **Fa** | The building itself (Chapel Street brick) |
| Customer Service | Violet `#6b3fa0` | **CS** | Warm and human, clearly not "money" or "stock" |

How the feed shows who is doing what:

- **The roster is a row of five seats at the desk.** A seat lights up in its agent's tint when the agent is working, and a pulsing ring shows it's "thinking". A small "…" badge means it's waiting on a colleague, and a green ✓ means it reported back. Each seat has a live one-line status written in plain English: "Checking the shelves", "Waiting on Accounting", "Reported to Boss".
- **Indentation shows the chain of command.** A specialist the boss asked is indented one step, and someone *they* asked is indented two. You can see the delegation tree without drawing one.
- **Hand-offs look different from talk.** A hand-off row shows two monograms with an arrow (`Bo → In`) and the task quoted in italic serif, like a note passed across the desk. Refused hand-offs (loop-backs the guardrails blocked) are dashed and greyed, so the guardrails stay visible without being noisy.
- **Tool calls are chips, with a plain-English verb next to the real call:** "checking the shelves `check_stock(sku=CC-TEE-WHITE, size=S)`". A non-technical person reads the verb and a grader reads the code. Tool results are folded away under "Inventory got 2 answers back" for anyone who wants the raw data.
- **Report-backs are framed cards in the agent's tint.** The boss's final resolution is the biggest card, set in serif, because it's the answer.

**Why:** the hardest part of a multi-agent system is telling *who said what to whom*. Colour plus monogram plus indentation gives three independent cues, so it still reads for colour-blind users (the monogram and indent carry it) and at a glance (the colour carries it).

---

## How resolved tickets show up

- When a run finishes, the backend marks the ticket `resolved` and the stub gets a **green rubber stamp, "RESOLVED"**, set at a slight angle and "thumped" on with a quick scale-down animation. The rail header updates ("2 open · 1 resolved"), the stub greys slightly, and the same stamp appears large next to the ticket title.
- The view switches by itself to the **Debrief**:
  1. **The boss's resolution** in large serif, with the status the boss set ("Boss set: Needs Approval"), so "resolved" never hides that a decision is still waiting.
  2. **The customer reply draft** in a dashed "Draft reply · not sent" box. The dashed border says "not final".
  3. **Open questions** the tools couldn't answer.
  4. **One card per agent:** who asked them, how many steps, their answer, the tools they "looked at", and who they handed off to. That is the "short summary of what each agent did".
  5. The facts the boss relied on, folded away.
- The token count for the run sits quietly next to the tabs, so cost is visible without being in the way.

**Why:** a stamp is the most physical, satisfying way to say "done". The debrief answers the question a manager actually asks after the fact: "who did what, and what do you need from me?"

---

## How cash shows up

- **The till card** shows the checking balance in large serif tabular figures, with a receipt-style zig-zag bottom edge.
- When a payment is approved, the number **counts down** over about a second, so you watch $3,400.00 roll to $2,560.00, and a red **−$840.00** chip pops in beside it. The change is felt, not just shown.
- A thin **cushion bar** under the balance fills in proportion to cash, with an amber tick at the shop's **$500 cushion**. If the balance drops below it, the number and bar turn red with "Below the $500 cushion the shop likes to keep." This matches the rule in the agents' prompts, so the people and the agents watch the same line.
- **"Waiting on you"** has a red count badge. Each approval card shows an icon, a plain title ("Pay vendor invoice", "Pay rent", "Buy a reprint"), the amount, the agent's one-line reason, and **risks in amber** (for example "with rent also paid, checking drops to $160"). Payable items get a big green **Approve $840.00** button that says the exact amount, so nobody approves blind. Reprint orders show editable vendor / SKU / size / qty fields, in case an agent left one out.
- Approving needs a name in **"Signing as"** in the top bar, which is remembered on this computer. The name becomes `approved_by` in the database. The button is disabled with a tooltip until a name is entered.
- Non-money decisions (a discount, sending a reply) appear in the tray with a muted note: "Your call, outside the till. No money moves from here." They're visible, but they can't be mistaken for payments.
- After approving, the card gets an **"Approved · money moved"** stamp, a toast confirms the new balance, and the **"Paid out"** ledger lists the payment with who signed and when.

**Why:** money is where a real business gets hurt, so it gets the most deliberate interaction: exact amounts on buttons, a named signer, visible risks, and an animation that makes the drop impossible to miss.

---

## The creative choices that make it feel special

- **Paper and ink, not dashboard grey.** A warm off-white "paper" background with very faint ruled lines, ivory cards, and a serif (Iowan / Palatino) for titles, money and the boss's words. It feels like a shop's order book, and it's calmer to sit at for a long time.
- **Tickets are tear-off stubs**, with a perforated dashed edge, a mono ticket number, and an emoji for the ticket type (🧾 order, 🏠 rent, 🏷️ discount), so the three tickets are recognisable at a glance.
- **The rubber stamp** for resolved tickets and approved payments. It's a small moment of satisfaction when something is finished.
- **The till counts down** like a cash register, and the receipt zig-zag sits under the balance.
- **People words, not system words:** "Start the team", "Team at work…", "Waiting on you", "Signing as", "Reset shop", "the team is working" with typing dots. The tool verbs read like a colleague ("pulling the invoice", "checking the till").
- **The shop day in the header** ("Shop day · Mon, Aug 31, 2026") is the desk date the agents use, not the computer's, so people and agents share one calendar.
- **Small, quick motion:** feed lines rise in, stamps thump, numbers roll. All animation is turned off when the operating system asks for reduced motion.
- **Friendly failure states:** if the backend is down, a banner says exactly which command to run. If a run was cut off by a server restart, the ticket says so and offers to run again.

## How it talks to the backend

- `frontend/src/api.ts` calls the FastAPI backend at `VITE_API_URL` (default `http://127.0.0.1:8000`, see `frontend/.env.example`). `backend/main.py` allows the Vite origins (`http://localhost:5173`, `http://127.0.0.1:5173`) through CORS.
- Board data (tickets, cash, payments, health) is polled every 4 s. During a run the floor polls `/api/events?ticket_id=…&since=…` every second and appends only new events. When the run's POST returns, the board refreshes, the ticket stamps, and the debrief opens.
- Start it with `npm run dev` in `hw5/frontend`, which opens `http://localhost:5173` in the browser.
