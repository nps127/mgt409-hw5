import type { AgentEvent, Cash, Health, Payment, Ticket, TicketSummary } from './types'

// The FastAPI backend (backend/main.py). Override with VITE_API_URL in frontend/.env.
export const API_URL = (import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000').replace(/\/$/, '')

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
  })
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`
    try {
      const body = await res.json()
      if (body?.detail) detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)
    } catch {
      /* not JSON */
    }
    throw new Error(detail)
  }
  return res.json() as Promise<T>
}

export const api = {
  health: () => call<Health>('/api/health'),
  tickets: () => call<Ticket[]>('/api/tickets'),
  cash: () => call<Cash>('/api/cash'),
  payments: () => call<Payment[]>('/api/payments'),
  summary: (ticketId: number) => call<TicketSummary>(`/api/tickets/${ticketId}/summary`),
  run: (ticketId: number) => call<unknown>(`/api/tickets/${ticketId}/run`, { method: 'POST' }),
  events: (params: { ticket_id?: number; run_id?: string; since?: string; limit?: number }) => {
    const q = new URLSearchParams()
    Object.entries(params).forEach(([k, v]) => v !== undefined && v !== null && q.set(k, String(v)))
    return call<AgentEvent[]>(`/api/events?${q}`)
  },
  approve: (body: Record<string, unknown>) =>
    call<{ ok: boolean; new_balance?: number }>('/api/approve', { method: 'POST', body: JSON.stringify(body) }),
  reset: () => call<{ ok: boolean }>('/api/reset', { method: 'POST' }),
}
