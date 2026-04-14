import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  ReferenceLine,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import type { ReactNode } from 'react'
import type { PredictionResponse } from '@/types/prediction'
import { formatCurrency, formatCurrencyBRL } from '@/lib/utils'
import { formatZipWithRegion } from '@/lib/zipcodeRegion'
import { MoneyText } from '@/components/prediction/MoneyText'
import { useCurrencyDisplayStore } from '@/store/useCurrencyDisplayStore'

// ── Geração da bell curve (normal aproximada) ─────────────────────────────────
// Fórmula: mean = p50, std = (p75 - p25) / 1.35   (quartil-a-desvio padrão)
// Gera N pontos entre p25 - 2σ e p75 + 2σ

function generateBellCurve(
  p25: number,
  p50: number,
  p75: number,
  numPoints = 60,
): Array<{ x: number; density: number }> {
  const mean = p50
  const std = Math.max((p75 - p25) / 1.35, 1)
  const xMin = p25 - 2 * (p50 - p25)
  const xMax = p75 + 2 * (p75 - p50)

  return Array.from({ length: numPoints }, (_, i) => {
    const x = xMin + (xMax - xMin) * (i / (numPoints - 1))
    const z = (x - mean) / std
    const density = Math.exp(-0.5 * z * z)
    return { x, density }
  })
}

function formatXAxis(value: number): string {
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`
  if (value >= 1_000) return `$${Math.round(value / 1_000)}k`
  return `$${value}`
}

// ── Obter percentis (backend ou estimativa) ───────────────────────────────────

function getPercentiles(prediction: PredictionResponse): {
  p25: number
  p50: number
  p75: number
  isEstimated: boolean
} {
  if (prediction.market_percentiles) {
    return { ...prediction.market_percentiles, isEstimated: false }
  }
  const p50 = prediction.zipcode_median_price ?? prediction.predicted_price
  return {
    p25: p50 * 0.80,
    p50,
    p75: p50 * 1.25,
    isEstimated: true,
  }
}

interface MarketContextProps {
  prediction: PredictionResponse
}

function ChartPriceTooltip({ x }: { x: number }) {
  const showBrl = useCurrencyDisplayStore((s) => s.showBrlParallel)
  const rate = useCurrencyDisplayStore((s) => s.usdToBrl)
  return (
    <div className="rounded-lg border border-border bg-card px-2.5 py-1.5 text-xs shadow">
      <p className="font-semibold tabular-nums text-foreground">{formatCurrency(x)}</p>
      {showBrl && (
        <p className="mt-0.5 tabular-nums text-muted-foreground">~ {formatCurrencyBRL(x * rate)}</p>
      )}
    </div>
  )
}

export function MarketContext({ prediction }: MarketContextProps) {
  const { p25, p50, p75, isEstimated } = getPercentiles(prediction)
  const curveData = generateBellCurve(p25, p50, p75)

  const similarCount = prediction.similar_count ?? null

  return (
    <div className="rounded-xl border border-border bg-card p-5 h-full flex flex-col">
      <div className="mb-4">
        <p className="text-sm font-semibold text-foreground">Contexto de Mercado</p>
        <p className="text-xs text-muted-foreground mt-0.5 leading-snug">
          Comparação com imóveis na mesma região postal ({formatZipWithRegion(prediction.zipcode)}).
        </p>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-3 gap-3 mb-4">
        <StatCell
          label="Mediana"
          value={<MoneyText usd={p50} layout="block" />}
          note={isEstimated ? '(estimada)' : undefined}
        />
        <StatCell
          label="Faixa IQR"
          value={
            <span className="flex flex-col gap-1 leading-tight">
              <span className="flex flex-wrap items-baseline gap-x-1 gap-y-0.5">
                <MoneyText usd={p25} layout="inline" />
                <span className="text-muted-foreground">–</span>
                <MoneyText usd={p75} layout="inline" />
              </span>
            </span>
          }
          note={isEstimated ? '(estimada)' : undefined}
        />
        <StatCell
          label="Similares"
          value={similarCount !== null ? String(similarCount) : '—'}
          note={similarCount !== null ? 'encontrados' : 'dados indisponíveis'}
        />
      </div>

      {/* Bell curve */}
      <div className="flex-1 min-h-0" style={{ minHeight: 120 }}>
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={curveData} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id="mktGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#6366f1" stopOpacity={0.4} />
                <stop offset="95%" stopColor="#6366f1" stopOpacity={0.02} />
              </linearGradient>
            </defs>

            <XAxis
              dataKey="x"
              type="number"
              domain={['dataMin', 'dataMax']}
              tickFormatter={formatXAxis}
              tick={{ fontSize: 9 }}
              tickLine={false}
              axisLine={false}
              tickCount={5}
            />
            <YAxis hide />

            <Tooltip
              content={({ active, payload }) => {
                if (!active || !payload?.length) return null
                const x = payload[0]?.payload?.x as number | undefined
                if (x === undefined) return null
                return <ChartPriceTooltip x={x} />
              }}
            />

            <Area
              type="monotone"
              dataKey="density"
              stroke="#6366f1"
              strokeWidth={2}
              fill="url(#mktGrad)"
              dot={false}
              isAnimationActive={false}
            />

            {/* Linha: preço previsto */}
            <ReferenceLine
              x={prediction.predicted_price}
              stroke="#7c3aed"
              strokeWidth={2}
              strokeDasharray="4 3"
              label={{
                value: 'Você',
                position: 'top',
                fontSize: 10,
                fill: '#7c3aed',
                fontWeight: 600,
              }}
            />

            {/* Linha: mediana */}
            <ReferenceLine
              x={p50}
              stroke="hsl(var(--muted-foreground))"
              strokeWidth={1}
              strokeDasharray="3 3"
              label={{
                value: 'Mediana',
                position: 'insideTopLeft',
                fontSize: 9,
                fill: 'hsl(var(--muted-foreground))',
              }}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {isEstimated && (
        <p className="text-[10px] text-muted-foreground mt-2">
          * Distribuição estimada — percentis reais disponíveis após Fase 0 do backend.
        </p>
      )}
    </div>
  )
}

function StatCell({
  label,
  value,
  note,
}: {
  label: string
  value: ReactNode
  note?: string
}) {
  return (
    <div className="rounded-lg bg-muted/40 px-3 py-2.5 min-w-0">
      <p className="text-[10px] font-medium text-muted-foreground">{label}</p>
      <div className="text-xs font-semibold text-foreground mt-0.5 leading-tight break-words">{value}</div>
      {note && <p className="text-[9px] text-muted-foreground mt-0.5">{note}</p>}
    </div>
  )
}
