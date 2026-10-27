export type UserRole = 'AUCTIONEER' | 'BIDDER'

export interface User {
  id: string
  name: string
  email: string
  role: UserRole
  created_at: string
}
