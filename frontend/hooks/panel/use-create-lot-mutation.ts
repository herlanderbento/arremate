"use client"

import { useMutation, useQueryClient } from "@tanstack/react-query"
import { api, toApiError } from "@/lib"
import type { ApiError } from "@/lib"
import type { Lot } from "@/types"

export interface CreateLotInput {
  external_id: string
  starting_bid: string
  min_increment: string
  starts_at: string
  ends_at: string
}

export function useCreateLotMutation() {
  const queryClient = useQueryClient()

  return useMutation<Lot, ApiError, CreateLotInput>({
    mutationFn: async (input) => {
      try {
        const { data } = await api.post<Lot>("/lots", input)
        return data
      } catch (error) {
        throw toApiError(error)
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["lots"] })
    },
  })
}
