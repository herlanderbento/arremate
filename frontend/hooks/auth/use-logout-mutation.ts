"use client"

import { useMutation, useQueryClient } from "@tanstack/react-query"
import { api } from "@/lib"
import { ME_QUERY_KEY } from "./use-me-query"

export function useLogoutMutation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => api.post("/auth/logout"),
    onSettled: () => {
      queryClient.clear()
      queryClient.setQueryData(ME_QUERY_KEY, null)
    },
  })
}
