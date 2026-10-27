"use client"

import { useMutation, useQueryClient } from "@tanstack/react-query"
import { api, toApiError } from "@/lib"
import type { ApiError } from "@/lib"
import type { Lot } from "@/types"

export function useCancelLotMutation() {
  const queryClient = useQueryClient()

  return useMutation<Lot, ApiError, string>({
    mutationFn: async (lotId) => {
      try {
        const { data } = await api.post<Lot>(`/lots/${lotId}/cancel`)
        return data
      } catch (error) {
        throw toApiError(error)
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["lots"] })
    },
  })
}
