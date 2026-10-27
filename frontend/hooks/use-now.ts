"use client"

import { useSyncExternalStore } from "react"

const TICK_MS = 1000

function subscribe(onTick: () => void) {
  const id = setInterval(onTick, TICK_MS)
  return () => clearInterval(id)
}

const getSnapshot = () => Math.floor(Date.now() / TICK_MS) * TICK_MS

// No clock on the server, so countdowns do not cause a hydration mismatch.
const getServerSnapshot = () => null

export function useNow(offsetMs = 0): number | null {
  const now = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot)
  return now === null ? null : now + offsetMs
}
