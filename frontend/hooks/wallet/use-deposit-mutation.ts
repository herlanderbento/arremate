"use client"

import { useMutation, useQueryClient } from "@tanstack/react-query"
import { api, toApiError } from "@/lib"
import type { ApiError } from "@/lib"
import type { Wallet } from "@/types"
import { WALLET_QUERY_KEY } from "./use-wallet-query"

export function useDepositMutation() {
  const queryClient = useQueryClient()

  return useMutation<Wallet, ApiError, string>({
    mutationFn: async (amount) => {
      try {
        const { data } = await api.post<Wallet>("/wallet/deposit", { amount })
        return data
      } catch (error) {
        throw toApiError(error)
      }
    },
    onSuccess: (wallet) => {
      queryClient.setQueryData(WALLET_QUERY_KEY, wallet)
    },
  })
}
