"use client"

import { keepPreviousData, useQuery } from "@tanstack/react-query"
import { api } from "@/lib"
import type { MyBid, Paginated } from "@/types"

export interface MyBidsParams {
  filter?: string
  page?: number
  per_page?: number
}

export function useMyBidsQuery(params: MyBidsParams, enabled = true) {
  return useQuery({
    queryKey: ["me", "bids", params],
    queryFn: async () => {
      const { data } = await api.get<Paginated<MyBid>>("/me/bids", {
        params: { ...params, filter: params.filter || undefined },
      })
      return data
    },
    enabled,
    placeholderData: keepPreviousData,
    staleTime: 0,
  })
}
