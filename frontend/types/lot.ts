export type Money = string

export type LotStatus = 'scheduled' | 'live' | 'ended' | 'cancelled'

export interface Lot {
  id: string
  title: string
  image_url: string | null
  attributes: { artist?: string; date?: string; medium?: string; [key: string]: unknown }
  status: LotStatus
  starting_bid: Money
  min_increment: Money
  current_bid: Money | null
  min_next_bid: Money
  bid_count: number
  starts_at: string
  ends_at: string
}

export interface BidHistoryItem {
  seq: number
  bidder_alias: string
  amount: Money
  created_at: string
}

export interface LotDetail extends Lot {
  server_time: string
  leader_alias: string | null
  my_alias: string | null
  bids: BidHistoryItem[]
}

export interface PlaceBidResult extends BidHistoryItem {
  ends_at: string
  extended: boolean
  min_next_bid: Money
  bid_count: number
  available: Money
}

export type LotRoomEvent =
  | ({ type: 'bid_placed'; lot_id: string; ends_at: string; min_next_bid: Money; bid_count: number } & BidHistoryItem)
  | { type: 'lot_extended'; lot_id: string; ends_at: string }
  | { type: 'lot_closed'; lot_id: string; winner_alias: string | null; final_amount: Money | null }
  | { type: 'lot_cancelled'; lot_id: string }

export type BidSituation = 'winning' | 'outbid' | 'won' | 'lost' | 'cancelled'

export interface MyBid extends Lot {
  my_max_bid: Money
  my_alias: string
  situation: BidSituation
  receipt_token: string | null
}

export interface Receipt {
  lot_id: string
  title: string
  image_url: string | null
  winner_alias: string
  amount: Money
  issued_at: string
  chain_head: string
  bid_count: number
  audit_url: string
}

export interface MyLot extends Lot {
  result: {
    sold: boolean
    final_amount: Money | null
    winner_alias: string | null
  }
}

export interface CatalogItem {
  external_id: string
  title: string
  image_url: string
  attributes: { artist?: string; date?: string; medium?: string; [key: string]: string | undefined }
}

export type IntegrityReason =
  | 'SEQ_GAP'
  | 'PREV_HASH_MISMATCH'
  | 'HASH_MISMATCH'
  | 'CHAIN_HEAD_MISMATCH'
  | 'LOT_STATE_MISMATCH'
  | 'RECEIPT_MISMATCH'

export interface LotAudit {
  lot_id: string
  title: string
  status: 'INTACT' | 'TAMPERED'
  chain_head: string
  issues: { seq: number | null; reason: IntegrityReason }[]
  bids: (BidHistoryItem & { hash: string; valid: boolean })[]
}
