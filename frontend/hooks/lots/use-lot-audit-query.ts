"use client"

import { useQuery } from "@tanstack/react-query"
import { api } from "@/lib"
import type { LotAudit } from "@/types"

export function useLotAuditQuery(lotId: string) {
  return useQuery({
    queryKey: ["audit", lotId],
    queryFn: async () => {
      const { data } = await api.get<LotAudit>(`/audit/lots/${lotId}`)
      return data
    },
    staleTime: 0,
    retry: false,
  })
}
