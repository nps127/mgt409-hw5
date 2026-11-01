import { useEffect, useRef, useState } from 'react'
import { money } from '../agents'
import type { Approval, Cash, Payment } from '../types'

// --- cash -----------------------------------------------------------------------

function useCountTo(target: number | null) {
  const [shown, setShown] = useState(target)
  const from = useRef(target)
  useEffect(() => {
    if (target === null) return
    if (from.current === null) {
      from.current = target
      setShown(target)
      return
    }
    const start = from.current
    const t0 = performance.now()
    let frame = 0
    const tick = (now: number) => {
      const p = Math.min(1, (now - t0) / 900)
      const eased = 1 - Math.pow(1 - p, 3)
      setShown(start + (target - start) * eased)
      if (p < 1) frame = requestAnimationFrame(tick)
      else from.current = target
    }
    frame = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(frame)
  }, [target])
  return shown
}

const CUSHION = 500

export function CashCard({ cash, delta }: { cash: Cash | null; delta: number | null }) {
  const shown = useCountTo(cash?.balance ?? null)
  const low = cash !== null && cash.balance < CUSHION
  return (
    <section className={`cash ${low ? 'low' : ''}`}>
      <span className="eyebrow">Checking · the till</span>
      <div className="cash-amount">
        {shown === null ? '—' : money(shown)}
        {delta !== null && delta !== 0 && (
          <span key={`${cash?.balance}`} className={`delta ${delta < 0 ? 'down' : 'up'}`}>
            {delta < 0 ? '−' : '+'}
            {money(Math.abs(delta))}
          </span>
        )}
      </div>
      <div className="cushion">
        <div className="cushion-bar">
          <span style={{ width: `${Math.min(100, ((cash?.balance ?? 0) / 3400) * 100)}%` }} />
          <i style={{ left: `${(CUSHION / 3400) * 100}%` }} title="$500 cushion" />
        </div>
        <small>
          {low ? 'Below the $500 cushion the shop likes to keep.' : `$500 cushion line marked · as of ${cash?.date ?? '—'}`}
        </small>
      </div>
    </section>
  )
}

// --- approvals ------------------------------------------------------------------

const KIND: Record<Approval['kind'], { label: string; icon: string; payable: boolean }> = {
  invoice_payment: { label: 'Pay vendor invoice', icon: '🧾', payable: true },
  rent_payment: { label: 'Pay rent', icon: '🏠', payable: true },
  reprint_order: { label: 'Buy a reprint', icon: '🖨️', payable: true },
  discount: { label: 'Approve a discount', icon: '🏷️', payable: false },
  customer_message: { label: 'Send a reply', icon: '✉️', payable: false },
  other: { label: 'Decision', icon: '❔', payable: false },
}

interface ApprovalProps {
  approvals: Approval[]
  approver: string
  busy: boolean
  onApprove: (a: Approval, edits: Partial<Approval>) => Promise<void>
}

function ApprovalCard({ a, approver, busy, onApprove }: { a: Approval } & Omit<ApprovalProps, 'approvals'>) {
  const k = KIND[a.kind] ?? KIND.other
  const [edits, setEdits] = useState<Partial<Approval>>({})
  const [working, setWorking] = useState(false)
  const merged = { ...a, ...edits }
  const missing =
    a.kind === 'reprint_order'
      ? !merged.vendor_id || !merged.sku || !merged.size || !merged.qty
      : !merged.ref_id
  const disabled = !approver.trim() || busy || working || missing

  return (
    <article className={`approval ${a.approved ? 'approved' : ''} ${k.payable ? '' : 'review'}`}>
      <header>
        <span className="approval-icon" aria-hidden>
          {k.icon}
        </span>
        <span>
          <b>{k.label}</b>
          {a.ticket_id && <small> · ticket #{a.ticket_id}</small>}
        </span>
        {a.amount !== null && <span className="approval-amount">{money(a.amount)}</span>}
      </header>
      <p>{a.summary}</p>
      {a.risks.length > 0 && (
        <ul className="risks">
          {a.risks.map((r, i) => (
            <li key={i}>{r}</li>
          ))}
        </ul>
      )}
      {a.kind === 'reprint_order' && !a.approved && (
        <div className="po">
          {(['vendor_id', 'sku', 'size', 'qty'] as const).map((f) => (
            <label key={f}>
              {f === 'vendor_id' ? 'vendor' : f}
              <input
                value={(merged[f] as string | number | null) ?? ''}
                onChange={(ev) =>
                  setEdits((e) => ({ ...e, [f]: f === 'vendor_id' || f === 'qty' ? Number(ev.target.value) || null : ev.target.value }))
                }
              />
            </label>
          ))}
        </div>
      )}
      {a.approved ? (
        <div className="approved-stamp">Approved · money moved</div>
      ) : k.payable ? (
        <button
          className="approve-btn"
          disabled={disabled}
          title={!approver.trim() ? 'Type your name in “Signing as” first' : missing ? 'Fill in the missing details' : ''}
          onClick={async () => {
            setWorking(true)
            try {
              await onApprove(a, edits)
            } finally {
              setWorking(false)
            }
          }}
        >
          {working ? 'Approving…' : `Approve${a.amount !== null ? ` ${money(a.amount)}` : ''}`}
        </button>
      ) : (
        <p className="review-note">Your call, outside the till. No money moves from here.</p>
      )}
    </article>
  )
}

export function ApprovalTray(props: ApprovalProps) {
  const pending = props.approvals.filter((a) => !a.approved && KIND[a.kind]?.payable).length
  return (
    <section className="tray">
      <div className="tray-head">
        <h3>Waiting on you</h3>
        {pending > 0 && <span className="badge">{pending}</span>}
      </div>
      {!props.approvals.length ? (
        <p className="muted small">Nothing to sign. When the team needs money moved, it lands here and waits for a person.</p>
      ) : (
        props.approvals.map((a) => <ApprovalCard key={a.id} a={a} {...props} />)
      )}
    </section>
  )
}

// --- ledger ---------------------------------------------------------------------

export function Ledger({ rows }: { rows: Payment[] }) {
  if (!rows.length) return null
  return (
    <section className="ledger">
      <span className="eyebrow">Paid out</span>
      <ul>
        {rows.slice(0, 6).map((p) => (
          <li key={p.id}>
            <span>
              {p.kind === 'rent' ? `Rent · lease ${p.ref_id}` : `Invoice #${p.ref_id}`}
              <small>
                signed by {p.approved_by} · {p.paid_at}
              </small>
            </span>
            <b>−{money(p.amount)}</b>
          </li>
        ))}
      </ul>
    </section>
  )
}
