import { Skeleton } from '@/components/ui/skeleton'

/**
 * Espelha exatamente o layout do MainContent quando há resultado.
 * Mostrado enquanto a API está respondendo.
 */
export function PredictionSkeleton() {
  return (
    <div className="space-y-4">
      {/* PriceCard — dark gradient card */}
      <Skeleton className="h-36 w-full rounded-2xl" />

      {/* PropertySummary — 5 badges com ícone */}
      <div className="grid grid-cols-5 gap-3">
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} className="h-[84px] rounded-xl" />
        ))}
      </div>

      {/* ConfidenceGauge (2/5) + WhyThisPrice (3/5) */}
      <div className="grid grid-cols-5 gap-4">
        <Skeleton className="col-span-2 h-56 rounded-xl" />
        <Skeleton className="col-span-3 h-56 rounded-xl" />
      </div>

      {/* MarketContext (3/5) + FeatureImportance (2/5) */}
      <div className="grid grid-cols-5 gap-4">
        <Skeleton className="col-span-3 h-56 rounded-xl" />
        <Skeleton className="col-span-2 h-56 rounded-xl" />
      </div>
    </div>
  )
}
