"use client"

import { keepPreviousData, useQuery } from "@tanstack/react-query"
import { api } from "@/lib"
import type { Lot, Paginated } from "@/types"

export type LotsStatusFilter = "live" | "scheduled" | "ended"

export interface LotsParams {
  status?: LotsStatusFilter
  filter?: string
  page?: number
  per_page?: number
}

export const lotsQueryKey = (params: LotsParams) => ["lots", params] as const

export function useLotsQuery(params: LotsParams) {
  return useQuery({
    queryKey: lotsQueryKey(params),
    queryFn: async () => {
      const { data } = await api.get<Paginated<Lot>>("/lots", {
        params: { ...params, filter: params.filter || undefined },
      })
      return data
    },
    placeholderData: keepPreviousData,
    staleTime: 15_000,
    refetchInterval: 30_000,
  })
}
