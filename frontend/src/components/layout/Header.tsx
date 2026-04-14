import { useState } from 'react'
import { Moon, Sun, X, ExternalLink, Database, Cpu, MessageSquare, Menu, MessageCircle } from 'lucide-react'
import { useTheme } from '@/hooks/useTheme'

interface HeaderProps {
  onMenuClick?: () => void
  onChatClick?: () => void
}

export function Header({ onMenuClick, onChatClick }: HeaderProps) {
  const { isDark, toggle } = useTheme()
  const [aboutOpen, setAboutOpen] = useState(false)

  return (
    <>
      <header className="flex items-center justify-between border-b border-border bg-card px-6 py-3 shrink-0">
        <div>
          <h1 className="text-lg font-bold tracking-tight text-foreground sm:text-xl">
            Demetrio — madeinweb
          </h1>
          <p className="text-xs text-muted-foreground mt-0.5 max-w-md">
            Previsão de preço (King County) com contexto de mercado e assistente de IA.
          </p>
        </div>

        {/* Ações */}
        <div className="flex items-center gap-2">
          {/* Hamburger — visível abaixo de xl */}
          {onMenuClick && (
            <button
              onClick={onMenuClick}
              className="flex h-8 w-8 items-center justify-center rounded-lg border border-border bg-background text-muted-foreground transition-colors hover:bg-muted hover:text-foreground xl:hidden"
              aria-label="Abrir menu"
            >
              <Menu className="h-4 w-4" />
            </button>
          )}
          {/* Chat toggle — visível entre md e xl */}
          {onChatClick && (
            <button
              onClick={onChatClick}
              className="flex h-8 w-8 items-center justify-center rounded-lg border border-border bg-background text-muted-foreground transition-colors hover:bg-muted hover:text-foreground hidden md:flex xl:hidden"
              aria-label="Abrir chat"
            >
              <MessageCircle className="h-4 w-4" />
            </button>
          )}

          {/* Sobre */}
          <button
            onClick={() => setAboutOpen(true)}
            className="rounded-lg border border-border bg-background px-3 py-1.5 text-xs font-medium text-foreground transition-colors hover:bg-muted"
          >
            Sobre
          </button>

          {/* Dark / Light toggle */}
          <button
            onClick={toggle}
            title={isDark ? 'Modo claro' : 'Modo escuro'}
            className="flex h-8 w-8 items-center justify-center rounded-lg border border-border bg-background text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
            aria-label="Toggle theme"
          >
            {isDark ? <Sun className="h-3.5 w-3.5" /> : <Moon className="h-3.5 w-3.5" />}
          </button>

          {/* Avatar */}
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-violet-600 to-purple-700 text-[10px] font-bold text-white select-none">
            DM
          </div>
        </div>
      </header>

      {/* Modal Sobre */}
      {aboutOpen && <AboutModal onClose={() => setAboutOpen(false)} />}
    </>
  )
}

/* ── Modal "Sobre" ── */
function AboutModal({ onClose }: { onClose: () => void }) {
  return (
    /* Overlay */
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm"
      onClick={onClose}
    >
      {/* Card */}
      <div
        className="relative w-full max-w-md rounded-2xl border border-border bg-card p-6 shadow-2xl mx-4"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Fechar */}
        <button
          onClick={onClose}
          className="absolute right-4 top-4 flex h-7 w-7 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
        >
          <X className="h-4 w-4" />
        </button>

        {/* Header do modal */}
        <div className="flex items-center gap-3 mb-5">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-violet-600 to-purple-700">
            <span className="text-sm font-bold text-white">DM</span>
          </div>
          <div>
            <h2 className="text-base font-bold text-foreground">Demetrio — madeinweb</h2>
            <p className="text-xs text-muted-foreground">2014-2015 dados</p>
          </div>
        </div>

        <p className="text-sm text-muted-foreground leading-relaxed mb-5">
          Ferramenta de análise inteligente de imóveis que combina Machine Learning,
           RAG e um chat com LLM para entregar previsões
          de preço com contexto sobre o mercado
        </p>

        {/* Tech stack */}
        <div className="space-y-2 mb-5">
          <p className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">
            Stack técnico
          </p>
          <div className="grid grid-cols-2 gap-2">
            <TechBadge icon={Cpu} label="XGBoost" sub="R² ≈ 0.89 · MAE ~$68k" />
            <TechBadge icon={Database} label="FastAPI + RAG" sub="Python · LangChain" />
            <TechBadge icon={MessageSquare} label="LLM" sub="Explicações e chat" />
            <TechBadge icon={Cpu} label="React + Vite" sub="TypeScript · Tailwind" />
          </div>
        </div>

        {/* Model metrics */}
        <div className="rounded-xl bg-muted/50 p-3 mb-5">
          <p className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground mb-2">
            Métricas do modelo
          </p>
          <div className="grid grid-cols-3 gap-3 text-center">
            <Metric label="R²" value="≈ 0.89" />
            <Metric label="MAE" value="~$68k" />
            <Metric label="Dataset" value="21.6k" sub="imóveis" />
          </div>
        </div>

        {/* GitHub link placeholder */}
        <a
          href="https://github.com/Demetriobc"
          target="_blank"
          rel="noopener noreferrer"
          className="flex w-full items-center justify-center gap-2 rounded-lg border border-border py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
        >
          <ExternalLink className="h-4 w-4" />
          Ver código no GitHub
        </a>
      </div>
    </div>
  )
}

function TechBadge({
  icon: Icon,
  label,
  sub,
}: {
  icon: React.ElementType
  label: string
  sub: string
}) {
  return (
    <div className="flex items-start gap-2 rounded-lg border border-border bg-background px-3 py-2">
      <Icon className="h-4 w-4 text-primary shrink-0 mt-0.5" />
      <div>
        <p className="text-xs font-semibold text-foreground leading-none">{label}</p>
        <p className="text-[10px] text-muted-foreground mt-0.5 leading-tight">{sub}</p>
      </div>
    </div>
  )
}

function Metric({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div>
      <p className="text-[10px] text-muted-foreground">{label}</p>
      <p className="text-sm font-bold text-foreground">{value}</p>
      {sub && <p className="text-[10px] text-muted-foreground">{sub}</p>}
    </div>
  )
}
