import { AGENT_ORDER, TOOL_VERBS, agentMeta } from '../agents'
import type { TicketSummary } from '../types'

export function Debrief({ summary }: { summary: TicketSummary }) {
  const r = summary.resolution
  const agents = [...summary.agents].sort((a, b) => AGENT_ORDER.indexOf(a.agent) - AGENT_ORDER.indexOf(b.agent))
  return (
    <div className="debrief">
      {r && (
        <section className="resolution">
          <header>
            <span className="eyebrow">Boss’s resolution</span>
            <span className="pill open">boss set: {r.final_status.replace(/_/g, ' ')}</span>
          </header>
          <p className="lede">{r.summary}</p>
          {r.customer_reply_draft && (
            <div className="draft">
              <span className="eyebrow">Draft reply · not sent</span>
              <p>{r.customer_reply_draft}</p>
            </div>
          )}
          {r.open_questions.length > 0 && (
            <div className="questions">
              <span className="eyebrow">Open questions</span>
              <ul>
                {r.open_questions.map((q, i) => (
                  <li key={i}>{q}</li>
                ))}
              </ul>
            </div>
          )}
        </section>
      )}

      <div className="crew">
        {agents.map((a) => {
          const m = agentMeta(a.agent)
          return (
            <article key={a.agent} className="crew-card" style={{ ['--agent' as string]: m.color, ['--tint' as string]: m.tint }}>
              <header>
                <span className="avatar">{m.initials}</span>
                <span>
                  <b>{m.label}</b>
                  <small>
                    {a.asked_by.length ? `asked by ${a.asked_by.map((x) => agentMeta(x).label).join(', ')}` : 'started the ticket'}
                    {' · '}
                    {a.steps} step{a.steps === 1 ? '' : 's'}
                  </small>
                </span>
              </header>
              {a.answer && <p className="crew-answer">{a.answer}</p>}
              <div className="crew-meta">
                {a.tools.length > 0 && (
                  <div>
                    <span className="eyebrow">Looked at</span>
                    <div className="chips">
                      {a.tools.map((t) => (
                        <span key={t} className="chip small" title={TOOL_VERBS[t]}>
                          <code>{t}</code>
                        </span>
                      ))}
                    </div>
                  </div>
                )}
                {a.delegated_to.length > 0 && (
                  <div>
                    <span className="eyebrow">Handed off to</span>
                    <div className="chips">
                      {a.delegated_to.map((d) => (
                        <span key={d} className="chip small agent-chip" style={{ ['--agent' as string]: agentMeta(d).color }}>
                          {agentMeta(d).label}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </article>
          )
        })}
      </div>

      {r && r.facts.length > 0 && (
        <details className="facts">
          <summary>Facts the boss relied on ({r.facts.length})</summary>
          <ul>
            {r.facts.map((f, i) => (
              <li key={i}>{f}</li>
            ))}
          </ul>
        </details>
      )}
    </div>
  )
}
