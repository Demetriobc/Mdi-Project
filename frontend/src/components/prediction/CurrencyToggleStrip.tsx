import { Switch } from '@/components/ui/switch'
import { useCurrencyDisplayStore } from '@/store/useCurrencyDisplayStore'

export function CurrencyToggleStrip() {
  const showBrl = useCurrencyDisplayStore((s) => s.showBrlParallel)
  const usdToBrl = useCurrencyDisplayStore((s) => s.usdToBrl)
  const setShow = useCurrencyDisplayStore((s) => s.setShowBrlParallel)
  const setRate = useCurrencyDisplayStore((s) => s.setUsdToBrl)

  return (
    <div className="flex flex-col gap-3 rounded-xl border border-border bg-card/80 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
      <div className="min-w-0 space-y-0.5">
        <p className="text-sm font-medium text-foreground">Valores nos gráficos</p>
        <p className="text-xs text-muted-foreground leading-snug">
          Os dados do modelo são em <span className="text-foreground/80">US$</span>. Ative para ver também uma{' '}
          <span className="text-foreground/80">referência em R$</span> (cotação aproximada — não é câmbio oficial).
        </p>
      </div>
      <div className="flex flex-col items-stretch gap-2 sm:items-end shrink-0">
        <label className="flex cursor-pointer items-center justify-end gap-2">
          <span className="text-xs font-medium text-foreground whitespace-nowrap">Mostrar R$</span>
          <Switch checked={showBrl} onCheckedChange={setShow} aria-label="Mostrar referência em real" />
        </label>
        {showBrl && (
          <label className="flex items-center gap-2 text-xs text-muted-foreground">
            <span className="whitespace-nowrap">1 US$ ≈</span>
            <input
              type="number"
              min={1}
              max={20}
              step={0.01}
              value={usdToBrl}
              onChange={(e) => setRate(Number(e.target.value))}
              className="input-base w-20 py-1 text-xs tabular-nums"
              aria-label="Cotação aproximada reais por dólar"
            />
            <span className="whitespace-nowrap">R$</span>
          </label>
        )}
      </div>
    </div>
  )
}
