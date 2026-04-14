import { AlertCircle } from 'lucide-react'
import type { PredictionResponse } from '@/types/prediction'
import { formatCurrency, formatCurrencyBRL } from '@/lib/utils'
import { useCurrencyDisplayStore } from '@/store/useCurrencyDisplayStore'

interface FeatureRow {
  name: string
  value: number   // US$ (real ou estimado)
  isEstimated: boolean
}

function getImpactLabel(absValue: number): { label: string; cls: string } {
  if (absValue > 100_000) return { label: 'Alto', cls: 'bg-violet-500/10 text-violet-600 dark:text-violet-400' }
  if (absValue > 30_000)  return { label: 'Médio', cls: 'bg-amber-500/10 text-amber-600 dark:text-amber-400' }
  return { label: 'Baixo', cls: 'bg-slate-500/10 text-slate-500 dark:text-slate-400' }
}

function featureName(raw: string): string {
  const MAP: Record<string, string> = {
    sqft_living: 'Área interna',
    grade: 'Qualidade construtiva',
    zipcode: 'Localização (ZIP / região)',
    lat: 'Latitude',
    long: 'Longitude',
    sqft_above: 'Área acima do solo',
    bathrooms: 'Banheiros',
    bedrooms: 'Quartos',
    floors: 'Andares',
    view: 'Vista',
    condition: 'Condição',
    waterfront: 'Frente p/ água',
    yr_built: 'Ano de construção',
    yr_renovated: 'Ano de reforma',
    sqft_basement: 'Porão',
    sqft_lot: 'Terreno',
    sqft_living15: 'Área útil vizinhos (média)',
  }
  return MAP[raw] ?? raw.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

/** Derivar impactos em US$ a partir dos dados disponíveis. */
function deriveRows(prediction: PredictionResponse): { rows: FeatureRow[]; isEstimated: boolean } {
  // Fase 0: shap_contributions reais
  if (prediction.shap_contributions && Object.keys(prediction.shap_contributions).length > 0) {
    const rows = Object.entries(prediction.shap_contributions)
      .map(([name, value]) => ({ name, value, isEstimated: false }))
      .sort((a, b) => Math.abs(b.value) - Math.abs(a.value))
      .slice(0, 6)
    return { rows, isEstimated: false }
  }

  // Fallback: importância global escalada pelo preço previsto
  // importance_i é normalizada entre 0-1; escalamos pelo preço para ter a mesma unidade
  const total = Object.values(prediction.top_features).reduce((s, v) => s + v, 0)
  const rows = Object.entries(prediction.top_features)
    .map(([name, importance]) => ({
      name,
      value: (importance / (total || 1)) * prediction.predicted_price,
      isEstimated: true,
    }))
    .sort((a, b) => Math.abs(b.value) - Math.abs(a.value))
    .slice(0, 6)

  return { rows, isEstimated: true }
}

interface WhyThisPriceProps {
  prediction: PredictionResponse
}

export function WhyThisPrice({ prediction }: WhyThisPriceProps) {
  const { rows, isEstimated } = deriveRows(prediction)
  const showBrl = useCurrencyDisplayStore((s) => s.showBrlParallel)
  const usdToBrl = useCurrencyDisplayStore((s) => s.usdToBrl)

  const maxAbs = Math.max(...rows.map((r) => Math.abs(r.value)), 1)

  return (
    <div className="rounded-xl border border-border bg-card p-5 h-full min-h-[280px] flex flex-col">
      <div className="mb-4">
        <p className="text-sm font-semibold text-foreground">Por que este preço?</p>
        <p className="text-xs text-muted-foreground mt-1 leading-snug">
          Contribuição aproximada de cada fator em relação ao preço estimado (barras proporcionais entre si;
          não são preços isolados).
        </p>
      </div>

      <ul className="space-y-2.5 flex-1 min-h-0">
        {rows.map(({ name, value }) => {
          const { label, cls } = getImpactLabel(Math.abs(value))
          const barWidth = (Math.abs(value) / maxAbs) * 100
          const isPositive = value >= 0

          return (
            <li
              key={name}
              className="rounded-lg border border-border/70 bg-muted/25 px-3 py-2.5"
            >
              <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between sm:gap-3">
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${cls}`}>
                      {label}
                    </span>
                    <span className="text-xs font-medium text-foreground leading-snug break-words">
                      {featureName(name)}
                    </span>
                  </div>
                  <div className="mt-2 h-2.5 w-full overflow-hidden rounded-full bg-background/80 ring-1 ring-border/50">
                    <div
                      className={`h-full rounded-full transition-all ${
                        isPositive ? 'bg-emerald-500' : 'bg-red-500'
                      }`}
                      style={{ width: `${Math.max(barWidth, 2)}%` }}
                    />
                  </div>
                </div>
                <div
                  className={`shrink-0 text-right text-sm font-bold tabular-nums sm:min-w-[8.5rem] ${
                    isPositive ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-500'
                  }`}
                >
                  <span>
                    {isPositive ? '+' : '−'}
                    {formatCurrency(Math.abs(value))}
                  </span>
                  {showBrl && (
                    <span className="mt-0.5 block text-[11px] font-semibold opacity-90">
                      {isPositive ? '+' : '−'}
                      {formatCurrencyBRL(Math.abs(value) * usdToBrl)}
                    </span>
                  )}
                </div>
              </div>
            </li>
          )
        })}
      </ul>

      {/* Nota de estimativa */}
      {isEstimated && (
        <div className="mt-4 flex items-start gap-1.5 rounded-lg bg-muted/50 p-2.5">
          <AlertCircle className="h-3.5 w-3.5 shrink-0 text-muted-foreground mt-0.5" />
          <p className="text-[10px] text-muted-foreground leading-relaxed">
            Valores estimados a partir da importância global do modelo. Para valores exatos por
            predição, ative os SHAP contributions no backend (Fase 0).
          </p>
        </div>
      )}
    </div>
  )
}
