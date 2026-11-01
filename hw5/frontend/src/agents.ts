import type { AgentName } from './types'

export interface AgentMeta {
  name: AgentName
  label: string
  role: string
  initials: string
  color: string
  tint: string
}

// Each agent has its own colour and monogram, used everywhere it appears.
export const AGENTS: Record<AgentName, AgentMeta> = {
  boss: { name: 'boss', label: 'Boss', role: 'Runs the desk', initials: 'Bo', color: '#00356b', tint: '#e6edf6' },
  inventory: { name: 'inventory', label: 'Inventory', role: 'Stockroom', initials: 'In', color: '#2e7d4f', tint: '#e5f3ea' },
  accounting: { name: 'accounting', label: 'Accounting', role: 'Books & cash', initials: 'Ac', color: '#b26a00', tint: '#fbf0dc' },
  facilities: { name: 'facilities', label: 'Facilities', role: 'Lease & space', initials: 'Fa', color: '#a8452f', tint: '#f8e7e2' },
  customer_service: {
    name: 'customer_service',
    label: 'Customer Service',
    role: 'Front counter',
    initials: 'CS',
    color: '#6b3fa0',
    tint: '#efe8f8',
  },
}

export const AGENT_ORDER: AgentName[] = ['boss', 'inventory', 'accounting', 'facilities', 'customer_service']

export function agentMeta(name: string): AgentMeta {
  return (
    AGENTS[name as AgentName] ?? {
      name: name as AgentName,
      label: name === 'human' ? 'You' : name,
      role: '',
      initials: name === 'human' ? 'You' : name.slice(0, 2),
      color: '#4a5263',
      tint: '#eceef2',
    }
  )
}

// Plain-English verbs for MCP tools, so the feed reads like people working.
export const TOOL_VERBS: Record<string, string> = {
  get_ticket: 'reading the ticket',
  list_tickets: 'scanning the ticket queue',
  get_shop_date: 'checking today’s date',
  update_ticket: 'updating the ticket',
  check_stock: 'checking the shelves',
  get_pricing: 'looking up prices',
  list_vendors: 'checking vendors',
  get_invoice: 'pulling the invoice',
  get_cash_balance: 'checking the till',
  list_payments: 'checking payment history',
  get_lease: 'reading the lease',
  record_payment: 'recording a payment',
  record_purchase: 'recording a purchase',
}

export const TICKET_TYPES: Record<string, { label: string; icon: string }> = {
  customer_order: { label: 'Customer order', icon: '🧾' },
  rent_notice: { label: 'Rent notice', icon: '🏠' },
  price_override: { label: 'Discount request', icon: '🏷️' },
  vendor_bill: { label: 'Vendor bill', icon: '📦' },
}

export const money = (n: number | null | undefined) =>
  n === null || n === undefined
    ? '—'
    : n.toLocaleString('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 2 })
