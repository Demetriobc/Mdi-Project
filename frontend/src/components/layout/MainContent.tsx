import { usePredictionStore } from '@/store/usePredictionStore'
import { PriceCard } from '@/components/prediction/PriceCard'
import { ConfidenceGauge } from '@/components/prediction/ConfidenceGauge'
import { PropertySummary } from '@/components/prediction/PropertySummary'
import { WhyThisPrice } from '@/components/prediction/WhyThisPrice'
import { MarketContext } from '@/components/prediction/MarketContext'
import { FeatureImportance } from '@/components/prediction/FeatureImportance'
import { Warnings } from '@/components/prediction/Warnings'
import { CurrencyToggleStrip } from '@/components/prediction/CurrencyToggleStrip'
import { PredictionSkeleton } from '@/components/prediction/PredictionSkeleton'
import { Home, Brain, Search, MessageCircle } from 'lucide-react'

export function MainContent() {
  const result = usePredictionStore((s) => s.result)
  const isLoading = usePredictionStore((s) => s.isLoading)

  if (isLoading) return <PredictionSkeleton />
  if (!result) return <WelcomeState />

  return (
    <div id="prediction-result" className="space-y-4">
      {/* ── Linha 1: PriceCard (largura total) ── */}
      <PriceCard prediction={result} />

      <CurrencyToggleStrip />

      {/* ── Linha 2: PropertySummary (5 badges) ── */}
      <PropertySummary prediction={result} />

      {/* ── Confiança + impacto: empilha em telas médias, lado a lado no xl ── */}
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-5">
        <div className="xl:col-span-2">
          <ConfidenceGauge prediction={result} />
        </div>
        <div className="xl:col-span-3 min-h-[280px]">
          <WhyThisPrice prediction={result} />
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-5">
        <div className="xl:col-span-3 min-h-[300px]">
          <MarketContext prediction={result} />
        </div>
        <div className="xl:col-span-2 min-h-[280px]">
          <FeatureImportance prediction={result} />
        </div>
      </div>

      {/* ── Linha 5: Warnings (condicional) ── */}
      {result.warnings && result.warnings.length > 0 && (
        <Warnings warnings={result.warnings} />
      )}

      {/* ── Footer: versão do modelo ── */}
      <p className="text-right text-xs text-muted-foreground pb-2">
        Modelo: {result.model_version}
      </p>
    </div>
  )
}

/* ── Welcome state ── */
function WelcomeState() {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-6 text-center py-16">
      <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/10">
        <Home className="h-8 w-8 text-primary" />
      </div>

      <div className="space-y-2 max-w-sm">
        <h2 className="text-xl font-semibold text-foreground">Pronto para avaliar</h2>
        <p className="text-sm text-muted-foreground leading-relaxed">
          Preencha os dados do imóvel no painel esquerdo e clique em{' '}
          <strong className="text-foreground">Prever Preço</strong> para ver a análise completa.
        </p>
      </div>

      <div className="grid grid-cols-3 gap-4 mt-2 w-full max-w-xs">
        <FeatureHighlight icon={Brain} label="XGBoost" sub="R² ≈ 0.89" />
        <FeatureHighlight icon={Search} label="RAG" sub="5 fontes" />
        <FeatureHighlight icon={MessageCircle} label="Chat" sub="IA" />
      </div>
    </div>
  )
}

function FeatureHighlight({
  icon: Icon,
  label,
  sub,
}: {
  icon: React.ElementType
  label: string
  sub: string
}) {
  return (
    <div className="flex flex-col items-center gap-1.5 rounded-xl border border-border bg-card p-3">
      <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10">
        <Icon className="h-4 w-4 text-primary" />
      </div>
      <p className="text-xs font-semibold text-foreground">{label}</p>
      <p className="text-[10px] text-muted-foreground">{sub}</p>
    </div>
  )
}
