export interface PageMeta {
  total: number
  current_page: number
  per_page: number
  last_page: number
}

export interface Paginated<T> {
  data: T[]
  meta: PageMeta
}
