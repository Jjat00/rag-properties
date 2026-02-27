import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatPrice(price: number | null, currency?: string | null): string {
  if (price == null) return "N/A"
  const cur = currency ?? "MXN"
  if (price >= 1_000_000) {
    const m = price / 1_000_000
    return `$${m % 1 === 0 ? m.toFixed(0) : m.toFixed(1)}M ${cur}`
  }
  if (price >= 1_000) {
    const k = price / 1_000
    return `$${k % 1 === 0 ? k.toFixed(0) : k.toFixed(0)}K ${cur}`
  }
  return `$${price.toLocaleString()} ${cur}`
}

export function formatScore(score: number): number {
  return Math.round(score * 100)
}

export function scoreColor(score: number): string {
  const pct = score * 100
  if (pct >= 75) return "text-green-400"
  if (pct >= 50) return "text-amber-400"
  return "text-red-400"
}

export function scoreBgColor(score: number): string {
  const pct = score * 100
  if (pct >= 75) return "bg-green-500/15 border-green-500/30"
  if (pct >= 50) return "bg-amber-500/15 border-amber-500/30"
  return "bg-red-500/15 border-red-500/30"
}
