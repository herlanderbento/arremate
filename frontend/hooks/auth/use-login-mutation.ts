"use client"

import { useMutation, useQueryClient } from "@tanstack/react-query"
import { api, ApiError, toApiError } from "@/lib"
import { User } from "@/types"
import { ME_QUERY_KEY } from "./use-me-query"

export interface LoginInput {
  email: string
  password: string
}

export async function login(input: LoginInput): Promise<User> {
  try {
    const { data } = await api.post<User>("/auth/login", input)
    return data
  } catch (error) {
    throw toApiError(error)
  }
}

export function useLoginMutation() {
  const queryClient = useQueryClient()
  return useMutation<User, ApiError, LoginInput>({
    mutationFn: login,
    onSuccess: (user) => {
      queryClient.clear()
      queryClient.setQueryData(ME_QUERY_KEY, user)
    },
  })
}
