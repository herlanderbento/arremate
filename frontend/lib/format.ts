const currency = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' })

const dateTime = new Intl.DateTimeFormat('pt-BR', { dateStyle: 'short', timeStyle: 'short' })

const time = new Intl.DateTimeFormat('pt-BR', { timeStyle: 'medium' })

export function formatMoney(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === '') return '—'
  return currency.format(Number(value))
}

export function formatDateTime(iso: string): string {
  return dateTime.format(new Date(iso))
}

export function formatTime(iso: string): string {
  return time.format(new Date(iso))
}

export function formatDuration(ms: number): string {
  const total = Math.max(0, Math.floor(ms / 1000))
  const days = Math.floor(total / 86400)
  const hours = Math.floor((total % 86400) / 3600)
  const minutes = Math.floor((total % 3600) / 60)
  const seconds = total % 60
  const pad = (n: number) => String(n).padStart(2, '0')
  if (days > 0) return `${days}d ${pad(hours)}:${pad(minutes)}:${pad(seconds)}`
  if (hours > 0) return `${pad(hours)}:${pad(minutes)}:${pad(seconds)}`
  return `${pad(minutes)}:${pad(seconds)}`
}

export function parseMoneyInput(raw: string): string | null {
  const value = raw.trim().replace(/\s/g, '').replace(',', '.')
  if (!/^\d+(\.\d{1,2})?$/.test(value)) return null
  const amount = Number(value)
  return amount > 0 ? amount.toFixed(2) : null
}
