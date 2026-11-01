import { AGENT_ORDER, TOOL_VERBS, agentMeta } from '../agents'
import type { AgentEvent, AgentName } from '../types'

export type SeatState = 'idle' | 'working' | 'waiting' | 'done' | 'error'
export interface Seat {
  state: SeatState
  activity: string
}

// Work out what each agent is doing from the event stream.
export function seatsFrom(events: AgentEvent[], live: boolean): Record<AgentName, Seat> {
  const seats = Object.fromEntries(
    AGENT_ORDER.map((a) => [a, { state: 'idle', activity: live ? 'Standing by' : 'Off the clock' } as Seat]),
  ) as Record<AgentName, Seat>
  for (const e of events) {
    const seat = seats[e.agent as AgentName]
    if (!seat) continue
    switch (e.kind) {
      case 'run_start':
        seats[e.agent as AgentName] = { state: 'working', activity: e.chain.length > 1 ? `Asked by ${agentMeta(e.chain[e.chain.length - 2]).label}` : 'Picked up the ticket' }
        break
      case 'model_response': {
        const tools = e.tool_calls.map((c) => c.tool).filter((t) => t !== 'delegate' && !t.startsWith('final_result'))
        if (tools.length) seats[e.agent as AgentName] = { state: 'working', activity: cap(TOOL_VERBS[tools[0]] ?? tools[0]) }
        else if (e.tool_calls.some((c) => c.tool.startsWith('final_result'))) seats[e.agent as AgentName] = { state: 'working', activity: 'Writing up' }
        break
      }
      case 'delegation':
        if (!e.note?.startsWith('refused')) {
          const to = e.tool_calls[0]?.to
          seats[e.agent as AgentName] = { state: 'waiting', activity: `Waiting on ${agentMeta(to ?? '').label}` }
        }
        break
      case 'tool_results':
        seats[e.agent as AgentName] = { state: 'working', activity: 'Thinking it over' }
        break
      case 'final':
        seats[e.agent as AgentName] = { state: 'done', activity: e.chain.length > 1 ? `Reported to ${agentMeta(e.chain[e.chain.length - 2]).label}` : 'Wrote the resolution' }
        break
      case 'error':
        seats[e.agent as AgentName] = { state: 'error', activity: 'Hit a problem' }
        break
    }
  }
  return seats
}

const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1)

export function Roster({ seats }: { seats: Record<AgentName, Seat> }) {
  return (
    <div className="roster">
      {AGENT_ORDER.map((name) => {
        const m = agentMeta(name)
        const seat = seats[name]
        return (
          <div key={name} className={`seat ${seat.state}`} style={{ ['--agent' as string]: m.color, ['--tint' as string]: m.tint }}>
            <span className="avatar">{m.initials}</span>
            <span className="seat-text">
              <b>{m.label}</b>
              <small>{seat.activity}</small>
            </span>
          </div>
        )
      })}
    </div>
  )
}
