import { Card, CardContent } from "@/components/ui/card"

function SkeletonCard() {
  return (
    <Card className="bg-card border-border animate-pulse">
      <CardContent className="p-4">
        <div className="flex items-start gap-3">
          <div className="w-12 h-12 rounded-full bg-muted" />
          <div className="flex-1 space-y-2">
            <div className="h-4 bg-muted rounded w-3/4" />
            <div className="h-3 bg-muted rounded w-1/2" />
            <div className="flex gap-3 mt-2">
              <div className="h-3 bg-muted rounded w-12" />
              <div className="h-3 bg-muted rounded w-12" />
              <div className="h-3 bg-muted rounded w-16" />
            </div>
            <div className="h-6 bg-muted rounded w-28 mt-2" />
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

export function LoadingSkeleton() {
  return (
    <div className="space-y-6">
      {/* Filter chips skeleton */}
      <div className="flex gap-2">
        <div className="h-6 bg-muted rounded-full w-24 animate-pulse" />
        <div className="h-6 bg-muted rounded-full w-20 animate-pulse" />
        <div className="h-6 bg-muted rounded-full w-28 animate-pulse" />
      </div>
      {/* Cards skeleton */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {Array.from({ length: 6 }, (_, i) => (
          <SkeletonCard key={i} />
        ))}
      </div>
    </div>
  )
}
