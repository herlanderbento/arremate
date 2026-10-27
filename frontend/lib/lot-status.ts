import type { Lot } from '@/types'

export type LotPhase = 'scheduled' | 'live' | 'closing' | 'ended' | 'cancelled'

export function lotPhase(lot: Pick<Lot, 'status' | 'starts_at' | 'ends_at'>, now: number | null): LotPhase {
  if (now === null || lot.status === 'ended' || lot.status === 'cancelled') return lot.status
  if (now >= Date.parse(lot.ends_at)) return 'closing'
  if (now >= Date.parse(lot.starts_at)) return 'live'
  return 'scheduled'
}
