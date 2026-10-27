import type { Money } from './lot'

export interface Wallet {
  balance: Money
  committed: Money
  available: Money
}
