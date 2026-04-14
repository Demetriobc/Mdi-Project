import { TrendingUp, TrendingDown } from 'lucide-react'
import { AreaChart, Area, ResponsiveContainer } from 'recharts'
import type { PredictionResponse } from '@/types/prediction'
import { formatCurrency, formatCurrencyBRL, formatPct } from '@/lib/utils'
import { formatZipRegionShort } from '@/lib/zipcodeRegion'
import { useCurrencyDisplayStore } from '@/store/useCurrencyDisplayStore'
import { MoneyText } from '@/components/prediction/MoneyText'

const SPARKLINE = [
  { v: 0.10 }, { v: 0.28 }, { v: 0.52 }, { v: 0.78 },
  { v: 1.00 }, { v: 0.82 }, { v: 0.60 }, { v: 0.35 }, { v: 0.12 },
]

interface PriceCardProps {
  prediction: PredictionResponse
}

export function PriceCard({ prediction }: PriceCardProps) {
  const {
    predicted_price,
    zipcode,
    price_vs_median_pct,
    zipcode_median_price,
    price_p10,
    price_p90,
  } = prediction

  const showBrl = useCurrencyDisplayStore((s) => s.showBrlParallel)
  const rate = useCurrencyDisplayStore((s) => s.usdToBrl)

  const hasMedian = price_vs_median_pct !== null && zipcode_median_price !== null
  const isAbove = hasMedian && price_vs_median_pct! >= 0

  return (
    <div className="relative rounded-2xl p-6 text-white">
      {/* Glow contido — não corta o texto no PDF */}
      <div
        className="pointer-events-none absolute inset-0 overflow-hidden rounded-2xl"
        aria-hidden
      >
        <div
          className="absolute inset-0 opacity-100"
          style={{
            background: 'linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%)',
          }}
        />
        <div className="absolute -right-16 -top-16 h-48 w-48 rounded-full bg-violet-600/20 blur-3xl" />
      </div>

      <div className="relative z-10 min-w-0">
        <p className="text-[11px] font-medium uppercase tracking-widest text-slate-400">
          Preço estimado
        </p>
        <p className="mt-1 text-xs font-medium normal-case tracking-normal text-slate-300/90">
          {formatZipRegionShort(zipcode)}
          <span className="mx-1.5 text-slate-500">·</span>
          <span className="tabular-nums text-slate-400">ZIP {zipcode}</span>
        </p>

        <div className="mt-2 flex items-end justify-between gap-4">
          <div className="min-w-0 flex-1">
            {/* Sem truncate — evita cortar dígitos em fontes grandes */}
            <p className="my-2 text-4xl font-black leading-[1.1] tracking-tight text-white break-words sm:text-5xl">
              {formatCurrency(predicted_price)}
            </p>
            {showBrl && (
              <p className="-mt-1 mb-2 text-lg font-semibold leading-tight text-slate-200 tabular-nums sm:text-xl">
                ~ {formatCurrencyBRL(predicted_price * rate)}
              </p>
            )}
            {price_p10 !== null && price_p90 !== null && (
              <p className="text-sm text-slate-400">
                <MoneyText usd={price_p10!} layout="inline" className="text-slate-300" />
                <span className="mx-1.5 text-slate-600">–</span>
                <MoneyText usd={price_p90!} layout="inline" className="text-slate-300" />
              </p>
            )}
          </div>

          <div className="h-14 w-28 shrink-0 opacity-50">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={SPARKLINE} margin={{ top: 0, right: 0, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="sparkGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#7c3aed" stopOpacity={0.9} />
                    <stop offset="95%" stopColor="#7c3aed" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <Area
                  type="monotone"
                  dataKey="v"
                  stroke="#a78bfa"
                  strokeWidth={2}
                  fill="url(#sparkGrad)"
                  dot={false}
                  isAnimationActive={false}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {hasMedian && (
          <div className="mt-4 flex flex-wrap items-center gap-3">
            <span
              className={`inline-flex max-w-full flex-wrap items-center gap-1.5 rounded-full px-3 py-1.5 text-sm font-semibold ${
                isAbove
                  ? 'bg-emerald-500/20 text-emerald-300'
                  : 'bg-red-500/20 text-red-300'
              }`}
            >
              {isAbove ? (
                <TrendingUp className="h-3.5 w-3.5 shrink-0" />
              ) : (
                <TrendingDown className="h-3.5 w-3.5 shrink-0" />
              )}
              <span className="break-words">
                {formatPct(price_vs_median_pct!)} vs mediana (
                <MoneyText
                  usd={zipcode_median_price!}
                  layout="inline"
                  brlClassName={
                    isAbove
                      ? 'text-emerald-200/95 ml-1 text-[0.85em] font-semibold'
                      : 'text-red-200/95 ml-1 text-[0.85em] font-semibold'
                  }
                />
                )
              </span>
            </span>
          </div>
        )}
      </div>
    </div>
  )
}
