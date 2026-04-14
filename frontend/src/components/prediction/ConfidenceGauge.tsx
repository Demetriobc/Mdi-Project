import type { PredictionResponse } from '@/types/prediction'
import { Badge } from '@/components/ui/badge'

// ── Derivar confiança do P10/P90 quando o backend ainda não envia o campo ──
function deriveConfidence(prediction: PredictionResponse) {
  if (prediction.confidence) return prediction.confidence

  const { predicted_price: price, price_p10: p10, price_p90: p90 } = prediction
  if (p10 === null || p90 === null) return { score: 70, label: 'Média', color: 'yellow' }

  const intervalPct = ((p90 - p10) / price) * 100
  if (intervalPct < 20) return { score: 85, label: 'Alta', color: 'green' }
  if (intervalPct < 35) return { score: 70, label: 'Média', color: 'yellow' }
  return { score: 50, label: 'Baixa', color: 'red' }
}

const STROKE_COLORS: Record<string, string> = {
  green: '#10b981',
  yellow: '#f59e0b',
  red: '#ef4444',
}

// SVG semicircle gauge — eixo horizontal, arco abre para cima
// startAngle = 180° (esquerda), endAngle = 0° (direita)
// A fórmula usa ângulos matemáticos convencionais (antihorário a partir da direita)
// No SVG: x = CX + R*cos(θ), y = CY - R*sin(θ)  (sin negativo porque y cresce para baixo)
// sweep-flag = 1 para seguir no sentido horário visual (esquerda → cima → direita)

const R = 58
const CX = 80
const CY = 74

function gaugePath(score: number): string {
  // Ângulo matemático cresce da direita para a esquerda (PI = esquerda, 0 = direita)
  // score 0% → ângulo PI (esquerda, início do arco)
  // score 100% → ângulo 0 (direita, fim do arco)
  const angle = Math.PI * (1 - score / 100)
  const endX = CX + R * Math.cos(angle)
  const endY = CY - R * Math.sin(angle)
  const startX = CX - R   // ponto esquerdo
  const startY = CY
  return `M ${startX} ${startY} A ${R} ${R} 0 0 1 ${endX.toFixed(2)} ${endY.toFixed(2)}`
}

const BG_PATH = `M ${CX - R} ${CY} A ${R} ${R} 0 0 1 ${CX + R} ${CY}`

interface ConfidenceGaugeProps {
  prediction: PredictionResponse
}

export function ConfidenceGauge({ prediction }: ConfidenceGaugeProps) {
  const confidence = deriveConfidence(prediction)
  const { score, label, color } = confidence
  const strokeColor = STROKE_COLORS[color] ?? '#6366f1'

  const badgeVariant =
    color === 'green' ? 'success' : color === 'red' ? 'destructive' : 'warning'

  return (
    <div className="rounded-xl border border-border bg-card p-5 flex flex-col h-full min-h-[280px]">
      <div>
        <p className="text-sm font-semibold text-foreground">Confiança da previsão</p>
        <p className="text-xs text-muted-foreground mt-1 leading-snug">
          Quão “estreita” é a faixa P10–P90 em torno do preço: faixa menor → confiança maior.
        </p>
      </div>

      <div className="relative mx-auto mt-4 flex-1 flex flex-col items-center justify-center">
        <svg width="180" height="108" viewBox="0 0 160 96" aria-label={`Confiança: ${score}%`}>
          <text x="6" y="93" fill="hsl(var(--muted-foreground))" style={{ fontSize: 8 }}>
            Baixa
          </text>
          <text x="64" y="93" fill="hsl(var(--muted-foreground))" style={{ fontSize: 8 }}>
            Média
          </text>
          <text x="118" y="93" fill="hsl(var(--muted-foreground))" style={{ fontSize: 8 }}>
            Alta
          </text>
          {/* Track — cor fixa para PDF/canvas; arco usa coordenadas CX/CY/R */}
          <path
            d={BG_PATH}
            fill="none"
            stroke="#64748b"
            strokeOpacity={0.45}
            strokeWidth="13"
            strokeLinecap="round"
          />
          {score > 0 && (
            <path
              d={gaugePath(Math.min(score, 99.9))}
              fill="none"
              stroke={strokeColor}
              strokeWidth="13"
              strokeLinecap="round"
            />
          )}
        </svg>

        <div className="absolute bottom-7 flex flex-col items-center">
          <p className="text-4xl font-black tabular-nums text-foreground leading-none">{score}%</p>
          <Badge variant={badgeVariant} className="mt-2 text-[11px]">
            {label}
          </Badge>
        </div>
      </div>

      <div className="mt-auto rounded-lg bg-muted/40 px-3 py-2 text-[11px] text-muted-foreground leading-relaxed">
        <span className="font-medium text-foreground/80">Como ler:</span> o modelo indica uma faixa de
        preço provável; quanto mais larga a faixa, mais incerteza (pontuação menor).
      </div>
    </div>
  )
}
