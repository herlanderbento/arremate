"use client"

import { useMutation, useQueryClient } from "@tanstack/react-query"
import { api, toApiError } from "@/lib"
import type { ApiError } from "@/lib"
import type { PlaceBidResult } from "@/types"
import { applyBid, lotQueryKey } from "./lot-cache"
import type { LotDetailView } from "./use-lot-query"

export function usePlaceBidMutation(lotId: string) {
  const queryClient = useQueryClient()

  return useMutation<PlaceBidResult, ApiError, string>({
    mutationFn: async (amount) => {
      try {
        const { data } = await api.post<PlaceBidResult>(`/lots/${lotId}/bids`, { amount })
        return data
      } catch (error) {
        throw toApiError(error)
      }
    },
    onSuccess: (bid) => {
      queryClient.setQueryData<LotDetailView>(lotQueryKey(lotId), (lot) =>
        lot ? { ...applyBid(lot, bid), my_alias: bid.bidder_alias } : lot
      )
      queryClient.invalidateQueries({ queryKey: ["wallet"] })
      queryClient.invalidateQueries({ queryKey: ["me", "bids"] })
    },
    onError: () => {
      queryClient.invalidateQueries({ queryKey: lotQueryKey(lotId) })
    },
  })
}
