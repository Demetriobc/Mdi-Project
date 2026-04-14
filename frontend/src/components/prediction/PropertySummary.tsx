import { BedDouble, Bath, Ruler, Star, MapPin } from 'lucide-react'
import type { PredictionResponse } from '@/types/prediction'
import { formatZipRegionShort } from '@/lib/zipcodeRegion'

const GRADE_LABELS: Record<number, string> = {
  1: 'Cabana', 2: 'Subpadrão', 3: 'Simples', 4: 'Baixo', 5: 'Razoável',
  6: 'Baixo-médio', 7: 'Médio', 8: 'Bom', 9: 'Melhor', 10: 'Muito bom',
  11: 'Custom', 12: 'Luxo', 13: 'Mansão',
}

interface PropertySummaryProps {
  prediction: PredictionResponse
}

export function PropertySummary({ prediction }: PropertySummaryProps) {
  const { bedrooms, bathrooms, sqft_living, grade, zipcode } = prediction

  const compact = [
    { icon: BedDouble, label: 'Quartos', value: String(bedrooms) },
    { icon: Bath, label: 'Banheiros', value: String(bathrooms) },
    { icon: Ruler, label: 'Área útil', value: `${sqft_living.toLocaleString()} sqft` },
    { icon: Star, label: 'Grade', value: `${grade} · ${GRADE_LABELS[grade] ?? grade}` },
  ]

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {compact.map(({ icon: Icon, label, value }) => (
          <div
            key={label}
            className="flex min-w-0 flex-col items-center gap-1.5 rounded-xl border border-border bg-card px-2 py-3 text-center sm:px-3"
          >
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary/10">
              <Icon className="h-4 w-4 text-primary" />
            </div>
            <p className="text-[10px] font-medium leading-none text-muted-foreground">{label}</p>
            <p className="w-full min-w-0 truncate text-sm font-semibold leading-tight text-foreground">
              {value}
            </p>
          </div>
        ))}
      </div>

      {/* Localização em linha própria: evita quebrar grid 5 colunas com texto longo */}
      <div className="flex min-w-0 gap-3 rounded-xl border border-border bg-card p-3 sm:p-4">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 self-start">
          <MapPin className="h-5 w-5 text-primary" />
        </div>
        <div className="min-w-0 flex-1 text-left">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
            Localização
          </p>
          <p className="mt-1 text-sm font-semibold leading-snug text-foreground break-words">
            {formatZipRegionShort(zipcode)}
          </p>
          <p className="mt-0.5 text-xs tabular-nums text-muted-foreground">ZIP {zipcode} · King County, WA</p>
        </div>
      </div>
    </div>
  )
}
