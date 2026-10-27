import type { BidHistoryItem, LotDetail } from "@/types"

export { lotQueryKey } from "./use-lot-query"

interface NewBid extends BidHistoryItem {
  ends_at: string
  min_next_bid: string
  bid_count: number
}

// The same bid arrives twice (POST response and WebSocket event): applied once, by seq.
export function applyBid<T extends LotDetail>(lot: T, bid: NewBid): T {
  if (lot.bids.some((b) => b.seq === bid.seq)) return lot
  if (lot.bids.length > 0 && bid.seq < lot.bids[0].seq) return lot

  const { seq, bidder_alias, amount, created_at } = bid
  return {
    ...lot,
    current_bid: amount,
    leader_alias: bidder_alias,
    min_next_bid: bid.min_next_bid,
    bid_count: bid.bid_count,
    ends_at: bid.ends_at,
    bids: [{ seq, bidder_alias, amount, created_at }, ...lot.bids],
  }
}
