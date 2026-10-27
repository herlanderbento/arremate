"use client"

import { useQuery } from "@tanstack/react-query"
import { api } from "@/lib"
import type { LotDetail } from "@/types"

export interface LotDetailView extends LotDetail {
  clock_offset_ms: number
}

export const lotQueryKey = (id: string) => ["lots", "detail", id] as const


export function useLotQuery(id: string) {
  return useQuery({
    queryKey: lotQueryKey(id),
    queryFn: async () => {
      const { data } = await api.get<LotDetail>(`/lots/${id}`)
      const lot: LotDetailView = { ...data, clock_offset_ms: Date.parse(data.server_time) - Date.now() }
      return lot
    },
    staleTime: 0,
    retry: (count, error) => {
      const status = (error as { response?: { status?: number } }).response?.status
      return status !== 404 && status !== 422 && count < 2
    },
  })
}
