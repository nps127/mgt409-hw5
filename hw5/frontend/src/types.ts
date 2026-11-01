export type AgentName = 'boss' | 'inventory' | 'accounting' | 'facilities' | 'customer_service'

export interface Ticket {
  id: number
  type: string
  requester: string
  subject: string
  status: string
  state: 'open' | 'resolved'
  notes: string | null
  created_at: string
}

export interface ToolCall {
  tool: string
  call_id?: string
  args?: Record<string, unknown>
  to?: string
  task?: string
}

export interface AgentEvent {
  time: string
  run_id: string
  ticket_id: number | null
  agent: AgentName | 'human'
  chain: string[]
  kind: string
  said: string | null
  tools_used: string[]
  tool_calls: ToolCall[]
  results: { tool: string; result: string }[]
  note: string | null
}

export interface Approval {
  id: number
  kind: 'invoice_payment' | 'rent_payment' | 'discount' | 'reprint_order' | 'customer_message' | 'other'
  ticket_id: number | null
  ref_id: number | null
  amount: number | null
  summary: string
  risks: string[]
  vendor_id: number | null
  sku: string | null
  size: string | null
  qty: number | null
  approved: boolean
}

export interface Resolution {
  ticket_id: number
  final_status: string
  summary: string
  agents_consulted: string[]
  facts: string[]
  actions_taken: string[]
  approvals_needed: Approval[]
  customer_reply_draft: string | null
  open_questions: string[]
}

export interface AgentSummary {
  agent: AgentName
  asked_by: string[]
  tasks: (string | null)[]
  tools: string[]
  delegated_to: string[]
  answer: string | null
  steps: number
  tokens: number
}

export interface TicketSummary {
  ticket_id: number
  run_id: string | null
  started?: string
  running: boolean
  interrupted?: boolean
  error?: string | null
  resolution?: Resolution | null
  agents: AgentSummary[]
  approvals: Approval[]
  run_usage?: Record<string, number>
}

export interface Cash {
  name: string
  balance: number
  date: string
}

export interface Health {
  ok: boolean
  model: string
  portkey_key_set: boolean
  database: string
  busy: boolean
  running_ticket: number | null
}

export interface Payment {
  id: number
  kind: string
  ref_id: number | null
  amount: number
  account: string
  paid_at: string
  approved_by: string
}
