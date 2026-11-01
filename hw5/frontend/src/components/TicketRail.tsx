import { TICKET_TYPES } from '../agents'
import type { Ticket } from '../types'

interface Props {
  tickets: Ticket[]
  selectedId: number | null
  runningId: number | null
  onSelect: (id: number) => void
}

export function TicketRail({ tickets, selectedId, runningId, onSelect }: Props) {
  const open = tickets.filter((t) => t.state === 'open').length
  return (
    <aside className="rail">
      <div className="rail-head">
        <h2>Tickets</h2>
        <span className="rail-count">{open} open · {tickets.length - open} resolved</span>
      </div>
      <ol className="stubs">
        {tickets.map((t) => {
          const type = TICKET_TYPES[t.type] ?? { label: t.type.replace(/_/g, ' '), icon: '📄' }
          const running = runningId === t.id
          return (
            <li key={t.id}>
              <button
                className={`stub ${selectedId === t.id ? 'selected' : ''} ${t.state} ${running ? 'running' : ''}`}
                onClick={() => onSelect(t.id)}
              >
                <span className="stub-no">#{t.id}</span>
                <span className="stub-type">
                  <span aria-hidden>{type.icon}</span> {type.label}
                </span>
                <span className="stub-subject">{t.subject}</span>
                <span className="stub-from">from {t.requester}</span>
                <span className="stub-foot">
                  {running ? (
                    <span className="pill live">
                      <i className="dot" /> team working
                    </span>
                  ) : t.state === 'resolved' ? (
                    <span className="pill done">resolved</span>
                  ) : (
                    <span className="pill open">{t.status.replace(/_/g, ' ')}</span>
                  )}
                </span>
                {t.state === 'resolved' && !running && <span className="stamp">Resolved</span>}
              </button>
            </li>
          )
        })}
      </ol>
    </aside>
  )
}
