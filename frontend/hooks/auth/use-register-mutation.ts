"use client"

import { useMutation, useQueryClient } from "@tanstack/react-query"
import { api, ApiError, toApiError } from "@/lib"
import { User, UserRole } from "@/types"
import { login } from "./use-login-mutation"
import { ME_QUERY_KEY } from "./use-me-query"

export interface RegisterInput {
  name: string
  email: string
  password: string
  role: UserRole
}

export function useRegisterMutation() {
  const queryClient = useQueryClient()
  return useMutation<User, ApiError, RegisterInput>({
    mutationFn: async (input) => {
      try {
        await api.post<User>("/auth/register", input)
      } catch (error) {
        throw toApiError(error)
      }
      return login({ email: input.email, password: input.password })
    },
    onSuccess: (user) => {
      queryClient.clear()
      queryClient.setQueryData(ME_QUERY_KEY, user)
    },
  })
}
