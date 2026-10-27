"use client"

import { useQuery } from "@tanstack/react-query"
import { api } from "@/lib"
import type { Receipt } from "@/types"

export function useReceiptQuery(token: string) {
  return useQuery({
    queryKey: ["receipts", token],
    queryFn: async () => {
      const { data } = await api.get<Receipt>(`/receipts/${token}`)
      return data
    },
    retry: false,
    staleTime: Infinity,
  })
}
