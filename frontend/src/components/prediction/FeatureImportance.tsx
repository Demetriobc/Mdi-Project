import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts'
import type { PredictionResponse } from '@/types/prediction'

function formatFeatureName(name: string): string {
  const MAP: Record<string, string> = {
    sqft_living: 'Área interna',
    grade: 'Grade',
    zipcode: 'Localização',
    lat: 'Latitude',
    long: 'Longitude',
    sqft_above: 'Área acima',
    bathrooms: 'Banheiros',
    bedrooms: 'Quartos',
    floors: 'Andares',
    view: 'Vista',
    condition: 'Condição',
    waterfront: 'Beira-mar',
    yr_built: 'Ano construção',
    yr_renovated: 'Reforma',
    sqft_basement: 'Porão',
    sqft_lot: 'Terreno',
    sqft_living15: 'Área vizinhos',
  }
  return MAP[name] ?? name.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

interface FeatureImportanceProps {
  prediction: PredictionResponse
  topN?: number
}

export function FeatureImportance({ prediction, topN = 8 }: FeatureImportanceProps) {
  const chartData = Object.entries(prediction.top_features)
    .sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]))
    .slice(0, topN)
    .map(([name, value]) => ({ name: formatFeatureName(name), value }))

  return (
    <div className="rounded-xl border border-border bg-card p-5 h-full flex flex-col">
      <div className="mb-4">
        <p className="text-sm font-semibold text-foreground">Fatores que mais influenciam</p>
        <p className="text-xs text-muted-foreground mt-1 leading-snug">
          Pesos globais do XGBoost (somam ~100%): quanto maior a barra, mais o modelo usa aquela variável nas
          decisões — não é valor em dólares.
        </p>
      </div>

      <div className="flex-1 min-h-0 w-full" style={{ minHeight: 220 }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={chartData}
            layout="vertical"
            margin={{ left: 4, right: 12, top: 4, bottom: 4 }}
            barCategoryGap={6}
          >
            <XAxis
              type="number"
              domain={[0, 'dataMax']}
              tick={{ fontSize: 10 }}
              tickLine={false}
              axisLine={false}
              tickFormatter={(v: number) => `${(v * 100).toFixed(0)}%`}
            />
            <YAxis
              dataKey="name"
              type="category"
              width={122}
              tick={{ fontSize: 10 }}
              tickLine={false}
              axisLine={false}
              interval={0}
            />
            <Tooltip
              formatter={(v) => [
                typeof v === 'number' ? `${(v * 100).toFixed(2)}%` : v,
                'Importância',
              ]}
              contentStyle={{
                background: 'hsl(var(--card))',
                border: '1px solid hsl(var(--border))',
                borderRadius: '8px',
                fontSize: '11px',
              }}
            />
            <ReferenceLine x={0} stroke="hsl(var(--border))" />
            <Bar
              dataKey="value"
              radius={[0, 4, 4, 0]}
              fill="hsl(var(--primary))"
              opacity={0.88}
              maxBarSize={22}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
