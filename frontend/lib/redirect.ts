import type { User } from '@/types'

export function afterLoginPath(user: User, next: string | null): string {
  // Only same-site paths: "//evil.com" or "https://…" would be an open redirect.
  if (next && next.startsWith('/') && !next.startsWith('//')) return next
  return user.role === 'AUCTIONEER' ? '/painel' : '/'
}
