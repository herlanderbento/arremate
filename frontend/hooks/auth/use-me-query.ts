"use client"

import { useQuery } from "@tanstack/react-query"
import { api, toApiError } from "@/lib"
import { User } from "@/types"

export const ME_QUERY_KEY = ["me"] as const

export function useMeQuery(enabled = true) {
  return useQuery<User | null, Error>({
    queryKey: ME_QUERY_KEY,
    queryFn: async () => {
      try {
        const { data } = await api.get<User>("/auth/me")
        return data
      } catch (error) {
        if (toApiError(error).status === 401) return null
        throw error
      }
    },
    enabled,
    retry: false,
  })
}
