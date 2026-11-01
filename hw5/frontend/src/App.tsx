import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { API_URL, api } from './api'
import { TICKET_TYPES } from './agents'
import { Debrief } from './components/Debrief'
import { Feed } from './components/Feed'
import { Roster, seatsFrom } from './components/Roster'
import { TicketRail } from './components/TicketRail'
import { ApprovalTray, CashCard, Ledger } from './components/Till'
import type { AgentEvent, Approval, Cash, Health, Payment, Ticket, TicketSummary } from './types'

const POLL_LIVE_MS = 1000
const POLL_BOARD_MS = 4000

export default function App() {
  const [tickets, setTickets] = useState<Ticket[]>([])
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [summary, setSummary] = useState<TicketSummary | null>(null)
  const [events, setEvents] = useState<AgentEvent[]>([])
  const [cash, setCash] = useState<Cash | null>(null)
  const [delta, setDelta] = useState<number | null>(null)
  const [payments, setPayments] = useState<Payment[]>([])
  const [health, setHealth] = useState<Health | null>(null)
  const [online, setOnline] = useState(true)
  const [runningId, setRunningId] = useState<number | null>(null)
  const [view, setView] = useState<'floor' | 'debrief'>('floor')
  const [approver, setApprover] = useState(() => localStorage.getItem('cc-approver') ?? '')
  const [toast, setToast] = useState<{ text: string; tone: 'ok' | 'bad' } | null>(null)
  const lastCash = useRef<number | null>(null)
  const sinceRef = useRef<string>('')

  const say = (text: string, tone: 'ok' | 'bad' = 'ok') => {
    setToast({ text, tone })
    window.setTimeout(() => setToast(null), 4500)
  }

  useEffect(() => localStorage.setItem('cc-approver', approver), [approver])

  // --- board-level data (tickets, cash, payments, health) ----------------------
  const refreshBoard = useCallback(async () => {
    try {
      const [t, c, p, h] = await Promise.all([api.tickets(), api.cash(), api.payments(), api.health()])
      setTickets(t)
      setPayments(p)
      setHealth(h)
      setOnline(true)
      if (lastCash.current !== null && c.balance !== lastCash.current) setDelta(c.balance - lastCash.current)
      lastCash.current = c.balance
      setCash(c)
      setRunningId((cur) => cur ?? h.running_ticket)
      setSelectedId((cur) => cur ?? (t.find((x) => x.state === 'open') ?? t[0])?.id ?? null)
    } catch {
      setOnline(false)
    }
  }, [])

  useEffect(() => {
    refreshBoard()
    const id = window.setInterval(refreshBoard, POLL_BOARD_MS)
    return () => window.clearInterval(id)
  }, [refreshBoard])

  // --- the selected ticket's last run ------------------------------------------
  const loadTicket = useCallback(async (ticketId: number) => {
    const s = await api.summary(ticketId)
    setSummary(s)
    if (s.run_id) {
      const ev = await api.events({ run_id: s.run_id, limit: 500 })
      setEvents(ev)
      sinceRef.current = ev.at(-1)?.time ?? ''
    } else {
      setEvents([])
      sinceRef.current = ''
    }
    return s
  }, [])

  useEffect(() => {
    if (selectedId === null) return
    loadTicket(selectedId)
      .then((s) => setView(s.run_id && !s.running ? 'debrief' : 'floor'))
      .catch(() => setSummary(null))
  }, [selectedId, loadTicket])

  // --- live polling while the team works the selected ticket -------------------
  const live = runningId !== null && runningId === selectedId
  useEffect(() => {
    if (!live || selectedId === null) return
    let stop = false
    const tick = async () => {
      try {
        const fresh = await api.events({ ticket_id: selectedId, since: sinceRef.current || undefined, limit: 500 })
        if (!stop && fresh.length) {
          sinceRef.current = fresh.at(-1)!.time
          setEvents((cur) => [...cur, ...fresh.filter((e) => e.run_id.startsWith('run-'))])
        }
      } catch {
        /* keep polling */
      }
    }
    const id = window.setInterval(tick, POLL_LIVE_MS)
    tick()
    return () => {
      stop = true
      window.clearInterval(id)
    }
  }, [live, selectedId])

  // If a run finishes while we weren't the one who started it (e.g. after a reload).
  useEffect(() => {
    if (runningId !== null && health && health.running_ticket === null && !health.busy) {
      const finished = runningId
      setRunningId(null)
      if (finished === selectedId) loadTicket(finished).then(() => setView('debrief'))
    }
  }, [health, runningId, selectedId, loadTicket])

  // --- actions ---------------------------------------------------------------------
  const start = async () => {
    if (selectedId === null || runningId !== null) return
    const ticketId = selectedId
    try {
      const last = await api.events({ ticket_id: ticketId, limit: 1 })
      sinceRef.current = last.at(-1)?.time ?? ''
    } catch {
      sinceRef.current = ''
    }
    setEvents([])
    setView('floor')
    setRunningId(ticketId)
    try {
      await api.run(ticketId)
      say(`Ticket #${ticketId} is done. Read the debrief.`)
    } catch (err) {
      say(`Ticket #${ticketId}: ${(err as Error).message}`, 'bad')
    } finally {
      setRunningId(null)
      await refreshBoard()
      if (ticketId === selectedIdRef.current) {
        await loadTicket(ticketId)
        setView('debrief')
      }
    }
  }
  const selectedIdRef = useRef(selectedId)
  selectedIdRef.current = selectedId

  const approve = async (a: Approval, edits: Partial<Approval>) => {
    const m = { ...a, ...edits }
    const body =
      a.kind === 'reprint_order'
        ? { action: 'purchase', vendor_id: m.vendor_id, sku: m.sku, size: m.size, qty: m.qty }
        : { action: 'payment', kind: a.kind === 'rent_payment' ? 'rent' : 'invoice', ref_id: m.ref_id }
    try {
      const res = await api.approve({ ...body, approved_by: approver.trim(), ticket_id: a.ticket_id ?? selectedId })
      say(`Approved. Checking is now ${res.new_balance?.toLocaleString('en-US', { style: 'currency', currency: 'USD' })}.`)
    } catch (err) {
      say((err as Error).message, 'bad')
    }
    await refreshBoard()
    if (selectedId !== null) setSummary(await api.summary(selectedId))
  }

  const reset = async () => {
    if (!window.confirm('Put the shop database back to its original state? Payments, ticket notes and statuses are undone. The audit trail is kept.')) return
    try {
      await api.reset()
      lastCash.current = null
      setDelta(null)
      say('Fresh start: the database is back to its original values.')
    } catch (err) {
      say((err as Error).message, 'bad')
    }
    await refreshBoard()
    if (selectedId !== null) await loadTicket(selectedId)
    setView('floor')
  }

  // --- render ----------------------------------------------------------------------
  const ticket = tickets.find((t) => t.id === selectedId) ?? null
  const seats = useMemo(() => seatsFrom(events, live), [events, live])
  const type = ticket ? TICKET_TYPES[ticket.type] ?? { label: ticket.type, icon: '📄' } : null
  const approvals = summary?.approvals ?? []
  const deskDate = cash?.date
    ? new Date(`${cash.date}T12:00:00`).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' })
    : ''

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="crest">CC</span>
          <span>
            <b>Campus Customs</b>
            <small>Operations desk · Chapel Street</small>
          </span>
        </div>
        <div className="topbar-mid">
          {deskDate && <span className="desk-date">Shop day · {deskDate}</span>}
          <span className={`conn ${online ? 'on' : 'off'}`} title={API_URL}>
            <i className="dot" /> {online ? `Backend connected · ${health?.model ?? ''}` : 'Backend offline'}
          </span>
        </div>
        <div className="topbar-right">
          <label className="signer">
            Signing as
            <input value={approver} placeholder="Your name" onChange={(e) => setApprover(e.target.value)} />
          </label>
          <button className="ghost" onClick={reset} disabled={runningId !== null}>
            Reset shop
          </button>
        </div>
      </header>

      {!online && (
        <div className="offline">
          Can’t reach the backend at <code>{API_URL}</code>. Start it from <code>hw5/backend</code> with{' '}
          <code>uvicorn main:app --reload --port 8000</code>.
        </div>
      )}

      <main className="layout">
        <TicketRail tickets={tickets} selectedId={selectedId} runningId={runningId} onSelect={setSelectedId} />

        <section className="floor">
          {ticket && type ? (
            <>
              <div className="ticket-head">
                <div>
                  <span className="eyebrow">
                    {type.icon} {type.label} · #{ticket.id}
                  </span>
                  <h1>{ticket.subject}</h1>
                  <p className="from">
                    from <b>{ticket.requester}</b>
                  </p>
                  {ticket.notes && <p className="notes">{ticket.notes.split(' | ')[0]}</p>}
                </div>
                <div className="ticket-cta">
                  {ticket.state === 'resolved' && !live && <span className="stamp big">Resolved</span>}
                  <button className="primary" onClick={start} disabled={runningId !== null || !online}>
                    {live ? (
                      <>
                        <i className="spinner" /> Team at work…
                      </>
                    ) : runningId !== null ? (
                      `Team busy on #${runningId}`
                    ) : summary?.run_id ? (
                      'Run the team again'
                    ) : (
                      'Start the team'
                    )}
                  </button>
                </div>
              </div>

              <Roster seats={seats} />

              <div className="tabs">
                <button className={view === 'floor' ? 'on' : ''} onClick={() => setView('floor')}>
                  Live floor {live && <i className="dot" />}
                </button>
                <button className={view === 'debrief' ? 'on' : ''} onClick={() => setView('debrief')} disabled={!summary?.run_id || live}>
                  Debrief
                </button>
                {summary?.run_usage?.total_tokens ? (
                  <span className="tokens">{summary.run_usage.total_tokens.toLocaleString()} tokens last run</span>
                ) : null}
              </div>

              {summary?.interrupted && !live && (
                <p className="warn">The last run on this ticket stopped before the boss finished (server restarted?). Run it again.</p>
              )}
              {summary?.error && <p className="warn">Last run ended with an error: {summary.error}</p>}

              {view === 'floor' || !summary?.run_id || live ? <Feed events={events} live={live} /> : <Debrief summary={summary} />}
            </>
          ) : (
            <div className="empty-feed">
              <p>Pick a ticket on the left.</p>
            </div>
          )}
        </section>

        <aside className="till">
          <CashCard cash={cash} delta={delta} />
          <ApprovalTray approvals={approvals} approver={approver} busy={runningId !== null} onApprove={approve} />
          {!approver.trim() && approvals.some((a) => !a.approved) && (
            <p className="hint">Type your name in “Signing as” to approve.</p>
          )}
          <Ledger rows={payments} />
        </aside>
      </main>

      {toast && <div className={`toast ${toast.tone}`}>{toast.text}</div>}
    </div>
  )
}
