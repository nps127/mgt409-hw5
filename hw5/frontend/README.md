# Campus Customs desk (frontend)

React + Vite + TypeScript dashboard for the HW5 agent team. Design notes: `../output/design.md`.

```bash
cd hw5/frontend
npm install        # first time only
npm run dev        # opens http://localhost:5173
```

The page calls the FastAPI backend at `VITE_API_URL` (default `http://127.0.0.1:8000`). Start the backend first, from `hw5/backend`, with `uvicorn main:app --reload --port 8000`.

| File | What it is |
| --- | --- |
| `src/App.tsx` | Page layout, polling, start / approve / reset actions |
| `src/api.ts` | Calls to the backend routes |
| `src/agents.ts` | Agent colours and monograms, tool verbs, money formatting |
| `src/components/TicketRail.tsx` | Ticket stubs with the resolved stamp |
| `src/components/Roster.tsx` | The five agent seats and their live status |
| `src/components/Feed.tsx` | Live feed of hand-offs, tool calls and reports |
| `src/components/Debrief.tsx` | The boss's resolution and a card per agent |
| `src/components/Till.tsx` | Cash balance, approvals tray, and paid-out ledger |
