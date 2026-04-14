import { useState, type ReactNode } from 'react'
import { usePrediction } from '@/hooks/usePrediction'
import { Loader2, Minus, Plus, ChevronDown, Home, Waves, X } from 'lucide-react'
import { KING_COUNTY_ZIP_OPTIONS, zipOsmEmbedUrl } from '@/lib/zipcodeRegion'
import { Slider } from '@/components/ui/slider'
import { Switch } from '@/components/ui/switch'
import { Collapsible, CollapsibleTrigger, CollapsibleContent } from '@/components/ui/collapsible'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'

const GRADE_LABELS: Record<number, string> = {
  1: 'Cabana', 2: 'Subpadrão', 3: 'Simples', 4: 'Baixo', 5: 'Razoável',
  6: 'Baixo médio', 7: 'Médio', 8: 'Bom', 9: 'Melhor', 10: 'Muito bom',
  11: 'Design custom', 12: 'Luxo', 13: 'Mansão',
}

const CONDITION_LABELS: Record<number, string> = {
  1: 'Péssima', 2: 'Ruim', 3: 'Média', 4: 'Boa', 5: 'Excelente',
}

const VIEW_LABELS: Record<number, string> = {
  0: 'Nenhuma', 1: 'Ruim', 2: 'Razoável', 3: 'Boa', 4: 'Excelente',
}

interface SidebarProps {
  onClose?: () => void
}

export function Sidebar({ onClose }: SidebarProps) {
  const { input, setInput, isLoading, error, submit } = usePrediction()
  const [advancedOpen, setAdvancedOpen] = useState(false)

  return (
    <aside className="flex w-72 shrink-0 flex-col border-r border-border bg-card">
      {/* ── Logo ── */}
      <div className="flex items-center gap-2.5 px-5 py-4 border-b border-border">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10 shrink-0">
          <Home className="h-4 w-4 text-primary" />
        </div>
        <span className="text-sm font-semibold text-foreground leading-tight">
          Demetrio — madeinweb
        </span>
        <Badge variant="ai" className="ml-auto text-[10px] px-1.5 py-0 shrink-0">AI</Badge>
        {onClose && (
          <button
            onClick={onClose}
            className="ml-1 flex h-6 w-6 shrink-0 items-center justify-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
            aria-label="Fechar"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        )}
      </div>

      {/* ── Formulário ── */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-5">
        <SectionLabel>Detalhes do Imóvel</SectionLabel>

        {/* Quartos + Banheiros */}
        <div className="grid grid-cols-2 gap-3">
          <Field label="Quartos">
            <Stepper
              value={input.bedrooms}
              min={1}
              max={10}
              onChange={(v) => setInput({ bedrooms: v })}
            />
          </Field>
          <Field label="Banheiros">
            <Stepper
              value={input.bathrooms}
              min={1}
              max={8}
              step={0.5}
              onChange={(v) => setInput({ bathrooms: v })}
            />
          </Field>
        </div>

        {/* Área interna */}
        <Field label={`Área interna: ${input.sqft_living.toLocaleString()} sqft`}>
          <div className="pt-1">
            <Slider
              min={300}
              max={12000}
              step={50}
              value={[input.sqft_living]}
              onValueChange={([v]) =>
                setInput({ sqft_living: v, sqft_above: v - input.sqft_basement })
              }
            />
          </div>
          <div className="flex justify-between text-[10px] text-muted-foreground mt-1">
            <span>300</span>
            <span>12.000</span>
          </div>
        </Field>

        {/* Andares */}
        <Field label="Andares">
          <Stepper
            value={input.floors}
            min={1}
            max={4}
            step={0.5}
            onChange={(v) => setInput({ floors: v })}
          />
        </Field>

        {/* Qualidade construtiva */}
        <Field
          label={`Qualidade construtiva (grade ${input.grade}): ${GRADE_LABELS[input.grade] ?? ''}`}
        >
          <div className="pt-1">
            <Slider
              min={1}
              max={13}
              step={1}
              value={[input.grade]}
              onValueChange={([v]) => setInput({ grade: v })}
            />
          </div>
          <div className="flex justify-between text-[10px] text-muted-foreground mt-1">
            <span>1 — Cabana</span>
            <span>13 — Mansão</span>
          </div>
        </Field>

        {/* Condição */}
        <Field label={`Condição: ${CONDITION_LABELS[input.condition] ?? input.condition}`}>
          <div className="pt-1">
            <Slider
              min={1}
              max={5}
              step={1}
              value={[input.condition]}
              onValueChange={([v]) => setInput({ condition: v })}
            />
          </div>
          <div className="flex justify-between text-[10px] text-muted-foreground mt-1">
            <span>Péssima</span>
            <span>Excelente</span>
          </div>
        </Field>

        {/* Frente para a água */}
        <div className="flex items-center justify-between rounded-lg border border-border bg-muted/30 px-3 py-2.5">
          <div className="flex items-center gap-2">
            <Waves className="h-4 w-4 text-muted-foreground" />
            <span className="text-sm text-foreground">Frente para a água</span>
          </div>
          <Switch
            checked={input.waterfront === 1}
            onCheckedChange={(v) => setInput({ waterfront: v ? 1 : 0 })}
          />
        </div>

        {/* Vista */}
        <Field label={`Vista: ${VIEW_LABELS[input.view] ?? input.view}`}>
          <div className="pt-1">
            <Slider
              min={0}
              max={4}
              step={1}
              value={[input.view]}
              onValueChange={([v]) => setInput({ view: v })}
            />
          </div>
          <div className="flex justify-between text-[10px] text-muted-foreground mt-1">
            <span>Nenhuma</span>
            <span>Excelente</span>
          </div>
        </Field>

        {/* Localização + mapa embutido (OpenStreetMap) */}
        <Field
          label="Localização"
          hint={
            <>
              <strong className="text-foreground/80">ZIP</strong> é o código postal regional (similar ao
              CEP). Escolha a área — base: King County, WA.
            </>
          }
        >
          <select
            value={input.zipcode}
            onChange={(e) => setInput({ zipcode: e.target.value })}
            className="input-base"
            aria-label="Região aproximada do imóvel"
          >
            {KING_COUNTY_ZIP_OPTIONS.map(({ code, name }) => (
              <option key={code} value={code}>
                {name} ({code})
              </option>
            ))}
          </select>
          <div className="mt-2 overflow-hidden rounded-lg border border-border bg-muted/40 shadow-inner">
            <p className="px-2 py-1 text-[10px] font-medium text-muted-foreground bg-muted/60 border-b border-border">
              Região no mapa
            </p>
            <div className="relative aspect-[5/3] w-full bg-muted">
              {zipOsmEmbedUrl(input.zipcode) ? (
                <iframe
                  title={`Mapa da região ZIP ${input.zipcode}`}
                  src={zipOsmEmbedUrl(input.zipcode)!}
                  className="absolute inset-0 h-full w-full border-0 grayscale-[20%] contrast-[1.05]"
                  loading="lazy"
                  referrerPolicy="no-referrer-when-downgrade"
                />
              ) : (
                <div className="flex h-full items-center justify-center text-[10px] text-muted-foreground">
                  Mapa indisponível para este código.
                </div>
              )}
            </div>
          </div>
        </Field>

        {/* ── Campos avançados ── */}
        <Collapsible open={advancedOpen} onOpenChange={setAdvancedOpen}>
          <CollapsibleTrigger className="flex w-full items-center justify-between py-1 text-[10px] font-semibold uppercase tracking-widest text-muted-foreground hover:text-foreground transition-colors">
            <span>Campos avançados</span>
            <ChevronDown
              className={cn('h-3.5 w-3.5 transition-transform duration-200', advancedOpen && 'rotate-180')}
            />
          </CollapsibleTrigger>

          <CollapsibleContent className="mt-4 space-y-4 overflow-hidden data-[state=open]:animate-none">
            <div className="grid grid-cols-2 gap-3">
              <Field label="Ano construção">
                <input
                  type="number"
                  value={input.yr_built}
                  min={1900}
                  max={2015}
                  onChange={(e) => setInput({ yr_built: Number(e.target.value) })}
                  className="input-base"
                />
              </Field>
              <Field label="Ano reforma">
                <input
                  type="number"
                  value={input.yr_renovated}
                  min={0}
                  max={2015}
                  onChange={(e) => setInput({ yr_renovated: Number(e.target.value) })}
                  className="input-base"
                />
              </Field>
            </div>

            <Field label="Área do terreno (sqft)">
              <input
                type="number"
                value={input.sqft_lot}
                min={500}
                max={200000}
                step={500}
                onChange={(e) => setInput({ sqft_lot: Number(e.target.value) })}
                className="input-base"
              />
            </Field>

            <Field label="Porão (sqft)">
              <input
                type="number"
                value={input.sqft_basement}
                min={0}
                max={5000}
                step={50}
                onChange={(e) => {
                  const v = Number(e.target.value)
                  setInput({ sqft_basement: v, sqft_above: input.sqft_living - v })
                }}
                className="input-base"
              />
            </Field>
          </CollapsibleContent>
        </Collapsible>
      </div>

      {/* ── Erro ── */}
      {error && (
        <div className="mx-4 mb-3 rounded-lg bg-destructive/10 px-3 py-2 text-xs text-destructive">
          {error}
        </div>
      )}

      {/* ── Botão + Footer ── */}
      <div className="border-t border-border p-4 space-y-3">
        <button
          onClick={submit}
          disabled={isLoading}
          className="flex w-full items-center justify-center gap-2 rounded-lg bg-gradient-to-r from-violet-600 to-purple-600 py-2.5 text-sm font-semibold text-white shadow-lg shadow-violet-500/25 transition-opacity hover:opacity-90 active:scale-[0.98] disabled:opacity-60"
        >
          {isLoading ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Calculando…
            </>
          ) : (
            'Prever Preço'
          )}
        </button>
        <p className="text-center text-[10px] text-muted-foreground">
          Modelo usado XGBoost 
        </p>
      </div>
    </aside>
  )
}

/* ── Sub-componentes locais ── */

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">
      {children}
    </p>
  )
}

function Field({
  label,
  hint,
  children,
}: {
  label: string
  hint?: ReactNode
  children: React.ReactNode
}) {
  return (
    <div className="space-y-1.5">
      <label className="block text-xs font-medium text-foreground/80 leading-none">{label}</label>
      {hint != null && (
        <p className="text-[10px] text-muted-foreground leading-relaxed">{hint}</p>
      )}
      {children}
    </div>
  )
}

interface StepperProps {
  value: number
  min?: number
  max?: number
  step?: number
  onChange: (v: number) => void
}

function Stepper({ value, min, max, step = 1, onChange }: StepperProps) {
  function decrement() {
    const next = Math.round((value - step) * 100) / 100
    if (min === undefined || next >= min) onChange(next)
  }
  function increment() {
    const next = Math.round((value + step) * 100) / 100
    if (max === undefined || next <= max) onChange(next)
  }

  return (
    <div className="flex items-center gap-1.5 rounded-lg border border-border bg-background px-1 py-1">
      <button
        type="button"
        onClick={decrement}
        disabled={min !== undefined && value <= min}
        className="flex h-6 w-6 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-muted hover:text-foreground disabled:opacity-40"
      >
        <Minus className="h-3 w-3" />
      </button>
      <span className="flex-1 text-center text-sm font-semibold text-foreground tabular-nums">
        {value}
      </span>
      <button
        type="button"
        onClick={increment}
        disabled={max !== undefined && value >= max}
        className="flex h-6 w-6 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-muted hover:text-foreground disabled:opacity-40"
      >
        <Plus className="h-3 w-3" />
      </button>
    </div>
  )
}
