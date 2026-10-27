"use client"

import { keepPreviousData, useQuery } from "@tanstack/react-query"
import { api } from "@/lib"
import type { Money, MyLot, Paginated } from "@/types"

export type MyLotsSort = "created_at" | "ends_at" | "current_bid" | "title"

export interface MyLotsParams {
  filter?: string
  page?: number
  per_page?: number
  sort?: MyLotsSort
  sort_dir?: "asc" | "desc"
}

export interface MyLotsPage extends Paginated<MyLot> {
  total_received: Money
}

export const MY_LOTS_QUERY_KEY = ["lots", "mine"] as const

export function useMyLotsQuery(params: MyLotsParams) {
  return useQuery({
    queryKey: [...MY_LOTS_QUERY_KEY, params],
    queryFn: async () => {
      const { data } = await api.get<MyLotsPage>("/lots/mine", {
        params: { ...params, filter: params.filter || undefined },
      })
      return data
    },
    placeholderData: keepPreviousData,
    staleTime: 0,
    refetchInterval: 30_000,
  })
}
