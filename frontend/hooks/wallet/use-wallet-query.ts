"use client"

import { useQuery } from "@tanstack/react-query"
import { api } from "@/lib"
import type { Wallet } from "@/types"

export const WALLET_QUERY_KEY = ["wallet"] as const

export function useWalletQuery(enabled = true) {
  return useQuery({
    queryKey: WALLET_QUERY_KEY,
    queryFn: async () => {
      const { data } = await api.get<Wallet>("/wallet")
      return data
    },
    enabled,
    staleTime: 0,
  })
}
