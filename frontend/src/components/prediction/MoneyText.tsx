import { formatCurrency, formatCurrencyBRL } from '@/lib/utils'
import { useCurrencyDisplayStore } from '@/store/useCurrencyDisplayStore'

type Layout = 'block' | 'inline'

/** Valor em US$ (número do backend); opcionalmente mostra linha ou sufixo em R$. */
export function MoneyText({
  usd,
  layout = 'block',
  className = '',
  brlClassName = 'text-[0.92em] font-medium text-muted-foreground tabular-nums',
}: {
  usd: number
  layout?: Layout
  className?: string
  brlClassName?: string
}) {
  const showBrl = useCurrencyDisplayStore((s) => s.showBrlParallel)
  const rate = useCurrencyDisplayStore((s) => s.usdToBrl)
  const brl = usd * rate

  if (!showBrl) {
    return <span className={className}>{formatCurrency(usd)}</span>
  }

  if (layout === 'inline') {
    return (
      <span className={className}>
        {formatCurrency(usd)}
        <span className={brlClassName}> (~ {formatCurrencyBRL(brl)})</span>
      </span>
    )
  }

  return (
    <span className={className}>
      <span className="tabular-nums">{formatCurrency(usd)}</span>
      <span className={`mt-0.5 block ${brlClassName}`}>~ {formatCurrencyBRL(brl)}</span>
    </span>
  )
}
