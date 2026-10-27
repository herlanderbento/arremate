"use client"

import { keepPreviousData, useQuery } from "@tanstack/react-query"
import { api } from "@/lib"
import type { CatalogItem, Paginated } from "@/types"

export function useCatalogSearchQuery(filter: string, page = 1) {
  return useQuery({
    queryKey: ["catalog", filter, page],
    queryFn: async () => {
      const { data } = await api.get<Paginated<CatalogItem>>("/catalog/search", {
        params: { filter, page, per_page: 12 },
      })
      return data
    },
    enabled: filter.length >= 2,
    placeholderData: keepPreviousData,
    staleTime: 5 * 60 * 1000,
    retry: false,
  })
}
