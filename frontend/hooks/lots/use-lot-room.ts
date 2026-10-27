"use client"

import { useQueryClient } from "@tanstack/react-query"
import { useEffect, useState } from "react"
import type { LotRoomEvent } from "@/types"
import { applyBid, lotQueryKey } from "./lot-cache"
import type { LotDetailView } from "./use-lot-query"

export type RoomConnection = "connecting" | "open" | "closed"

const WS_URL = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000"

// After every (re)connection the lot is refetched, so events missed while offline are not lost.
export function useLotRoom(lotId: string, enabled = true) {
  const queryClient = useQueryClient()
  const [connection, setConnection] = useState<RoomConnection>("connecting")
  const [lastEvent, setLastEvent] = useState<LotRoomEvent | null>(null)

  useEffect(() => {
    if (!enabled) return

    const key = lotQueryKey(lotId)
    let socket: WebSocket | null = null
    let retry: ReturnType<typeof setTimeout> | undefined
    let attempts = 0
    let stopped = false

    const handle = (event: LotRoomEvent) => {
      setLastEvent(event)
      switch (event.type) {
        case "bid_placed":
          queryClient.setQueryData<LotDetailView>(key, (lot) => (lot ? applyBid(lot, event) : lot))
          break
        case "lot_extended":
          queryClient.setQueryData<LotDetailView>(key, (lot) =>
            lot ? { ...lot, ends_at: event.ends_at } : lot
          )
          break
        case "lot_closed":
        case "lot_cancelled":
          queryClient.invalidateQueries({ queryKey: key })
          queryClient.invalidateQueries({ queryKey: ["wallet"] })
          queryClient.invalidateQueries({ queryKey: ["me", "bids"] })
          break
      }
    }

    const connect = () => {
      setConnection("connecting")
      socket = new WebSocket(`${WS_URL}/ws/lots/${lotId}`)
      socket.onopen = () => {
        attempts = 0
        setConnection("open")
        queryClient.invalidateQueries({ queryKey: key })
      }
      socket.onmessage = (message) => {
        try {
          handle(JSON.parse(message.data) as LotRoomEvent)
        } catch {
        }
      }
      socket.onclose = () => {
        if (stopped) return
        setConnection("closed")
        attempts += 1
        retry = setTimeout(connect, Math.min(30_000, 1000 * 2 ** attempts))
      }
    }

    connect()
    return () => {
      stopped = true
      clearTimeout(retry)
      socket?.close()
    }
  }, [lotId, enabled, queryClient])

  return { connection, lastEvent }
}
