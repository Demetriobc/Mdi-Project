import { AlertTriangle, Info, CheckCircle } from 'lucide-react'

// Heurística simples para detectar tipo de aviso pelo texto
function classifyWarning(text: string): 'warning' | 'info' | 'success' {
  const lower = text.toLowerCase()
  if (lower.includes('atenção') || lower.includes('antiga') || lower.includes('abaixo') || lower.includes('verificar')) {
    return 'warning'
  }
  if (lower.includes('sem') || lower.includes('impacto limitado')) {
    return 'info'
  }
  return 'warning'
}

const ICON_MAP = {
  warning: { Icon: AlertTriangle, cls: 'text-amber-500' },
  info:    { Icon: Info,          cls: 'text-blue-500'  },
  success: { Icon: CheckCircle,   cls: 'text-emerald-500' },
}

const BG_MAP = {
  warning: 'border-amber-500/30 bg-amber-500/5',
  info:    'border-blue-500/30 bg-blue-500/5',
  success: 'border-emerald-500/30 bg-emerald-500/5',
}

interface WarningsProps {
  warnings: string[]
}

export function Warnings({ warnings }: WarningsProps) {
  if (warnings.length === 0) return null

  return (
    <div className="space-y-2">
      <p className="text-sm font-semibold text-foreground">Pontos de atenção</p>
      <ul className="space-y-2">
        {warnings.map((text, i) => {
          const type = classifyWarning(text)
          const { Icon, cls } = ICON_MAP[type]
          const bg = BG_MAP[type]

          return (
            <li
              key={i}
              className={`flex items-start gap-2.5 rounded-xl border px-4 py-3 ${bg}`}
            >
              <Icon className={`mt-0.5 h-4 w-4 shrink-0 ${cls}`} />
              <span className="text-sm text-foreground leading-relaxed">{text}</span>
            </li>
          )
        })}
      </ul>
    </div>
  )
}
