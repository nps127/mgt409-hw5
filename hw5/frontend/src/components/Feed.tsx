import { useEffect, useRef } from 'react'
import { TOOL_VERBS, agentMeta } from '../agents'
import type { AgentEvent } from '../types'

function argText(args: Record<string, unknown> | undefined): string {
  if (!args) return ''
  return Object.entries(args)
    .filter(([, v]) => v !== null && v !== undefined && v !== '')
    .map(([k, v]) => `${k}=${typeof v === 'string' ? v : JSON.stringify(v)}`)
    .join(', ')
}

const time = (iso: string) => new Date(iso).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit', second: '2-digit' })

function Item({ e }: { e: AgentEvent }) {
  const m = agentMeta(e.agent)
  const depth = Math.max(0, e.chain.length - 1)
  const style = { ['--agent' as string]: m.color, ['--tint' as string]: m.tint, ['--depth' as string]: depth }
  const who = (
    <span className="who">
      <span className="avatar sm">{m.initials}</span>
      <b>{m.label}</b>
      <time>{time(e.time)}</time>
    </span>
  )

  if (e.kind === 'run_start') {
    if (depth > 0) return null // the hand-off row above already shows the task
    return (
      <li className="ev start" style={style}>
        {who}
        <p>Picked up the ticket and is reading it.</p>
      </li>
    )
  }

  if (e.kind === 'delegation') {
    const call = e.tool_calls[0] ?? {}
    const to = agentMeta(call.to ?? '')
    const refused = e.note?.startsWith('refused')
    return (
      <li className={`ev handoff ${refused ? 'refused' : ''}`} style={style}>
        <div className="handoff-line">
          <span className="avatar sm">{m.initials}</span>
          <span className="arrow">{refused ? '⇢' : '→'}</span>
          <span className="avatar sm" style={{ background: to.color }}>{to.initials}</span>
          <span>
            <b>{m.label}</b> {refused ? 'tried to ask' : 'asks'} <b style={{ color: to.color }}>{to.label}</b>
          </span>
          <time>{time(e.time)}</time>
        </div>
        {call.task && <blockquote>{call.task}</blockquote>}
        {refused && <p className="muted">Declined: {e.note?.replace(/^refused:\s*/, '')}</p>}
      </li>
    )
  }

  if (e.kind === 'model_response') {
    const tools = e.tool_calls.filter((c) => c.tool !== 'delegate' && !c.tool.startsWith('final_result'))
    if (!e.said && !tools.length) return null
    return (
      <li className="ev say" style={style}>
        {who}
        {e.said && <p className="bubble">{e.said}</p>}
        {tools.length > 0 && (
          <div className="chips">
            {tools.map((c, i) => (
              <span key={i} className="chip" title={argText(c.args)}>
                <span className="chip-verb">{TOOL_VERBS[c.tool] ?? c.tool}</span>
                <code>
                  {c.tool}({argText(c.args)})
                </code>
              </span>
            ))}
          </div>
        )}
      </li>
    )
  }

  if (e.kind === 'tool_results') {
    const results = e.results.filter((r) => r.tool !== 'delegate')
    if (!results.length) return null
    return (
      <li className="ev results" style={style}>
        <details>
          <summary>
            {m.label} got {results.length} answer{results.length > 1 ? 's' : ''} back:{' '}
            {results.map((r) => r.tool).join(', ')}
          </summary>
          {results.map((r, i) => (
            <pre key={i}>
              <b>{r.tool}</b> {r.result}
            </pre>
          ))}
        </details>
      </li>
    )
  }

  if (e.kind === 'final') {
    return (
      <li className={`ev final ${depth === 0 ? 'boss-final' : ''}`} style={style}>
        {who}
        <p className="final-label">{depth === 0 ? 'Resolution' : `Report back to ${agentMeta(e.chain[e.chain.length - 2]).label}`}</p>
        <p>{e.said}</p>
      </li>
    )
  }

  if (e.kind === 'error') {
    return (
      <li className="ev error" style={style}>
        {who}
        <p>{e.note}</p>
      </li>
    )
  }
  return null
}

export function Feed({ events, live }: { events: AgentEvent[]; live: boolean }) {
  const wrap = useRef<HTMLDivElement>(null)
  useEffect(() => {
    // Follow new events inside the feed only, so the page itself doesn't jump.
    if (live && wrap.current) wrap.current.scrollTop = wrap.current.scrollHeight
  }, [events.length, live])

  if (!events.length) {
    return (
      <div className="empty-feed">
        {live ? (
          <p>
            <i className="dot" /> Waking the team up…
          </p>
        ) : (
          <p>No one has worked this ticket yet. Press <b>Start the team</b> and you’ll see every hand-off and lookup here as it happens.</p>
        )}
      </div>
    )
  }
  return (
    <div className="feed-wrap" ref={wrap}>
      <ol className="feed">
        {events.map((e, i) => (
          <Item key={`${e.time}-${i}`} e={e} />
        ))}
        {live && (
          <li className="ev typing">
            <span className="typing-dots">
              <i />
              <i />
              <i />
            </span>
            the team is working
          </li>
        )}
      </ol>
    </div>
  )
}
