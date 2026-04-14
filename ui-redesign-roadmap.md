# UI Redesign Roadmap — madeinweb-teste

> Roadmap para transformar a interface Streamlit básica na UI moderna da referência visual,
> com layout 3 colunas, gauge de confiança, breakdown SHAP por feature, gráfico de distribuição de mercado
> e chat melhorado.

---

## Decisão de stack: Streamlit vs React

| Critério | Streamlit atual | React + shadcn/ui |
|---|---|---|
| Layout 3 colunas fixas | Limitado | ✓ Total controle |
| Gauge circular (78%) | Precisa de Plotly hack | ✓ Recharts nativo |
| Bell curve de mercado | Plotly hacky | ✓ Recharts nativo |
| SHAP breakdown com $ | Workaround CSS | ✓ Componente próprio |
| Dark/light mode | CSS global apenas | ✓ Tailwind + CSS variables |
| Botão +/- nos inputs | Não suportado | ✓ Nativo |
| Velocidade de iteração | Rápida | Média |
| Impressão na entrevista | Boa | Excelente |

**Recomendação: React + TypeScript**

O design da referência é claramente um app React. Tentar replicar no Streamlit vai consumir
mais tempo em workarounds CSS do que em funcionalidade real. Para entrevista, o React
é mais impressionante e mostra domínio do stack moderno.

**Stack escolhido:**
- **Bundler:** Vite (dev server rápido, sem overhead de SSR)
- **Framework:** React 18
- **UI Components:** shadcn/ui + Radix UI
- **Estilo:** Tailwind CSS
- **Gráficos:** Recharts
- **HTTP Client:** Axios ou fetch nativo
- **Estado:** Zustand (simples, sem Redux)
- **Tipagem:** TypeScript

O **backend FastAPI permanece 100% igual** — o frontend só consome a API.

---

## O que já existe vs. o que é novo

### Já existe (backend pronto)
- `POST /predict` → preço + p10/p90 + top_features + zipcode_median + price_vs_median_pct
- `POST /chat` → resposta LLM + sources
- `POST /chat/explain` → explicação automática
- `GET /health` → status dos componentes

### Precisa ser adicionado no backend (pequenas mudanças)

| Funcionalidade da UI | Mudança no backend |
|---|---|
| Gauge "78% Confiança" | Calcular score a partir do intervalo P10-P90 |
| "Por que este preço?" com US$ por feature | Endpoint novo: SHAP values por predição |
| Distribuição de mercado (bell curve) | Retornar percentis do zipcode |
| "Pontos de atenção" | Regras baseadas nos dados do imóvel |
| "24 imóveis similares encontrados" | Contar vizinhos no dataset |

Esses dados precisam ser adicionados ao `POST /predict` response ou em um novo endpoint
`POST /predict/details`.

---

## Fases de implementação

---

### FASE 0 — Preparar o backend (antes de qualquer frontend)

**Objetivo:** Garantir que a API retorne todos os dados que a nova UI precisa.

#### 0.1 — Adicionar SHAP values por predição

Hoje o modelo retorna importâncias SHAP **globais** (média de todo o dataset).
A UI precisa de importâncias **por predição individual** (quanto cada feature
contribuiu para ESTE imóvel específico).

**Onde mudar:** `app/ml/predict.py`

```python
# Hoje em PredictionResult:
top_features: dict[str, float]   # ex: {"sqft_living": 0.312, ...}  ← importância global

# Novo campo a adicionar:
shap_contributions: dict[str, float]  # ex: {"sqft_living": 186000, ...}  ← US$ por feature
```

**Como calcular:** Durante `predict_price()`, rodar o SHAP TreeExplainer no input
individual e retornar os valores em US$ (expm1 do valor SHAP × base_value).

#### 0.2 — Calcular confidence score

Derivado do intervalo P10-P90 já disponível:

```python
# No prediction_service.py ou predict.py
def _compute_confidence(price: float, p10: float, p90: float) -> dict:
    interval_pct = (p90 - p10) / price * 100
    if interval_pct < 20:   return {"score": 85, "label": "Alta",   "color": "green"}
    elif interval_pct < 35: return {"score": 70, "label": "Média",  "color": "yellow"}
    else:                    return {"score": 50, "label": "Baixa",  "color": "red"}
```

#### 0.3 — Adicionar percentis do zipcode para bell curve

No `metadata.json` já temos `zipcode_median_prices`. Precisamos adicionar percentis:

```python
# Em train.py, ao calcular zipcode_median_prices:
zipcode_stats = (
    X_train.assign(price=y_train.values)
    .groupby("zipcode")["price"]
    .agg(["median", lambda x: x.quantile(0.25), lambda x: x.quantile(0.75)])
    .rename(columns={"median": "p50", "<lambda_0>": "p25", "<lambda_1>": "p75"})
)
```

#### 0.4 — Gerar "Pontos de atenção" (regras simples)

```python
# No prediction_service.py
def _generate_warnings(house: HouseInput, zipcode_median: float) -> list[str]:
    warnings = []
    if house.yr_built < 1970:
        warnings.append("Construção antiga — verificar necessidade de reformas")
    if house.condition < 3:
        warnings.append("Condição abaixo da média regional")
    if house.view == 0:
        warnings.append("Sem vista privilegiada (impacto limitado no preço)")
    return warnings
```

#### 0.5 — Schema: adicionar novos campos ao PredictionResponse

```python
# app/api/schemas/prediction.py
class PredictionResponse(BaseModel):
    # ... campos existentes ...

    # Novos
    shap_contributions: dict[str, float] = {}   # US$ por feature
    confidence: dict = {}                        # {"score": 78, "label": "Alta", "color": "green"}
    market_percentiles: dict = {}                # {"p25": 500k, "p50": 550k, "p75": 720k}
    warnings: list[str] = []                     # pontos de atenção
    similar_count: int = 0                       # imóveis similares encontrados
```

**Tempo estimado da Fase 0: 4–6 horas**

---

### FASE 1 — Setup do projeto frontend

**Objetivo:** Estrutura base funcionando com TypeScript + shadcn/ui.

#### 1.1 — Criar projeto com Vite

```bash
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
```

#### 1.2 — Instalar Tailwind CSS

```bash
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
```

#### 1.3 — Instalar shadcn/ui

shadcn/ui suporta Vite — só precisa de um pequeno ajuste no `tsconfig.json`:

```bash
npm install -D @types/node
npx shadcn-ui@latest init
# Escolher: TypeScript, Default style, CSS variables, src/components/ui
npx shadcn-ui@latest add card button slider badge separator
```

#### 1.4 — Instalar demais dependências

```bash
npm install recharts axios zustand lucide-react
npm install -D @types/recharts
```

#### 1.5 — Estrutura de pastas do frontend

```
frontend/
├── index.html              ← entry point do Vite
├── vite.config.ts          ← proxy para a API (evita CORS em dev)
├── tailwind.config.ts
│
└── src/
    ├── main.tsx            ← ReactDOM.createRoot
    ├── App.tsx             ← layout raiz + ThemeProvider
    ├── index.css           ← variáveis CSS Tailwind + dark mode
    │
    ├── components/
    │   ├── layout/
    │   │   ├── Sidebar.tsx     ← formulário + logo + botão prever
    │   │   ├── Header.tsx      ← Olá! + botões Exportar/Sobre/Theme
    │   │   └── ChatPanel.tsx   ← painel direito do chat
    │   │
    │   ├── prediction/
    │   │   ├── PriceCard.tsx         ← card escuro com o preço principal
    │   │   ├── ConfidenceGauge.tsx   ← gauge circular 78%
    │   │   ├── PropertySummary.tsx   ← linha de ícones (quartos, banheiros...)
    │   │   ├── WhyThisPrice.tsx      ← breakdown SHAP com US$ por feature
    │   │   ├── MarketContext.tsx     ← tabela + bell curve do zipcode
    │   │   ├── FeatureImportance.tsx ← gráfico de barras horizontal
    │   │   └── Warnings.tsx          ← pontos de atenção
    │   │
    │   └── ui/                 ← componentes shadcn (auto-gerados)
    │
    ├── hooks/
    │   ├── usePrediction.ts    ← chamada ao /predict + estado
    │   └── useChat.ts          ← chamada ao /chat + histórico
    │
    ├── lib/
    │   ├── api.ts              ← axios instance + funções de API
    │   └── utils.ts            ← formatação de moeda, etc.
    │
    ├── store/
    │   └── usePredictionStore.ts ← Zustand store global
    │
    └── types/
        └── prediction.ts       ← tipos TypeScript que espelham os schemas Pydantic
```

#### 1.6 — Configurar variável de ambiente e proxy

```bash
# frontend/.env
VITE_API_URL=http://localhost:8001
```

```ts
// vite.config.ts — proxy evita CORS em desenvolvimento
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { '@': path.resolve(__dirname, './src') },
  },
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8001',
        rewrite: (p) => p.replace(/^\/api/, ''),
      },
    },
  },
})
```

**Tempo estimado da Fase 1: 2–3 horas**

---

### FASE 2 — Layout base e sidebar

**Objetivo:** Estrutura de 3 colunas com sidebar funcional.

#### 2.1 — Layout 3 colunas (page.tsx)

```tsx
// src/App.tsx
export default function App() {
  return (
    <div className="flex h-screen bg-background overflow-hidden">
      {/* Coluna 1: Sidebar (280px) */}
      <Sidebar className="w-72 shrink-0" />

      {/* Coluna 2: Conteúdo principal (flex-1) */}
      <main className="flex-1 overflow-y-auto">
        <Header />
        <div className="p-6">
          <PredictionContent />
        </div>
      </main>

      {/* Coluna 3: Chat (360px) */}
      <ChatPanel className="w-96 shrink-0 border-l" />
    </div>
  )
}
```

#### 2.2 — Sidebar com formulário

Componentes a construir:

- **Logo**: "madeinweb-teste" + badge "AI" roxo
- **Inputs com +/- buttons**: `NumberInput` customizado com Quartos, Banheiros
- **Range sliders**: Área útil (300–12000), Andares, Grade (3–13), Condição (1–5), Vista (0–4)
- **Toggle switch**: "Frente para a água"
- **Accordion**: "Campos avançados" (yr_built, sqft_lot, etc.)
- **Botão CTA**: "Prever Preço" com gradiente roxo, ícone de loading
- **Footer**: "Modelo: XGBoost • Atualizado: Nov 2024"

```tsx
// components/layout/Sidebar.tsx
const Sidebar = () => (
  <aside className="bg-card border-r flex flex-col h-full dark:bg-slate-900">
    <div className="p-4 border-b">
      <Logo />
    </div>
    <div className="flex-1 overflow-y-auto p-4 space-y-4">
      <SectionLabel>Detalhes do Imóvel</SectionLabel>
      <NumberInput label="Quartos" min={1} max={10} />
      <NumberInput label="Banheiros" min={0.5} max={8} step={0.5} />
      <RangeSlider label="Área útil (sqft)" min={300} max={12000} />
      {/* ... */}
      <Collapsible title="Campos avançados">
        {/* yr_built, sqft_lot, etc. */}
      </Collapsible>
    </div>
    <div className="p-4 border-t">
      <PredictButton />
    </div>
  </aside>
)
```

**Tempo estimado da Fase 2: 4–6 horas**

---

### FASE 3 — Cards de resultado principais

**Objetivo:** PriceCard + ConfidenceGauge + PropertySummary.

#### 3.1 — PriceCard (card escuro com gradiente)

```tsx
// components/prediction/PriceCard.tsx
const PriceCard = ({ prediction }: { prediction: PredictionResponse }) => (
  <div className="rounded-2xl p-6 text-white"
       style={{ background: 'linear-gradient(135deg, #1a1a2e, #16213e, #0f3460)' }}>
    <p className="text-xs tracking-widest text-slate-400 uppercase">
      Preço Estimado · Zipcode {prediction.zipcode}
    </p>
    <p className="text-5xl font-black my-3">
      {prediction.predicted_price_formatted}
    </p>
    {/* Mini sparkline (Recharts LineChart sem eixos) */}
    <MiniSparkline />
    <Badge variant={pct >= 0 ? "success" : "destructive"}>
      {pct >= 0 ? "+" : ""}{pct.toFixed(1)}% vs mediana ({median})
    </Badge>
  </div>
)
```

#### 3.2 — ConfidenceGauge (gauge circular)

```tsx
// components/prediction/ConfidenceGauge.tsx
// Usa Recharts RadialBarChart para o arco
const ConfidenceGauge = ({ confidence }) => (
  <Card>
    <CardHeader><CardTitle>Confiança da Previsão</CardTitle></CardHeader>
    <CardContent>
      <RadialBarChart
        cx="50%" cy="60%"
        innerRadius="60%" outerRadius="90%"
        startAngle={180} endAngle={0}
        data={[{ value: confidence.score, fill: colorByLabel(confidence.label) }]}
      >
        <RadialBar dataKey="value" />
      </RadialBarChart>
      <div className="text-center -mt-8">
        <p className="text-4xl font-bold">{confidence.score}%</p>
        <Badge>{confidence.label}</Badge>
      </div>
      <p className="text-xs text-muted-foreground text-center mt-2">
        Baseado em similares e estabilidade do mercado local.
      </p>
    </CardContent>
  </Card>
)
```

#### 3.3 — PropertySummary (linha de ícones)

```tsx
// components/prediction/PropertySummary.tsx
// 5 badges: Quartos | Banheiros | Área útil | Grade | Zipcode
const metrics = [
  { icon: BedDouble, label: "Quartos",    value: prediction.bedrooms },
  { icon: Bath,      label: "Banheiros",  value: prediction.bathrooms },
  { icon: Pencil,    label: "Área útil",  value: `${sqft_living.toLocaleString()} sqft` },
  { icon: Star,      label: "Grade",      value: `${grade} ${gradeLabel(grade)}` },
  { icon: MapPin,    label: "Zipcode",    value: zipcode },
]
```

**Tempo estimado da Fase 3: 4–5 horas**

---

### FASE 4 — Cards analíticos

**Objetivo:** WhyThisPrice + MarketContext + FeatureImportance + Warnings.

#### 4.1 — "Por que este preço?" (WhyThisPrice)

Mostra o impacto de cada feature em US$ com badge de impacto (Alto/Médio/Baixo).

```tsx
// components/prediction/WhyThisPrice.tsx
const featureRows = [
  { name: "Área útil",    impact: "Alto",  value: +186000 },
  { name: "Localização",  impact: "Alto",  value: +142000 },
  { name: "Condição",     impact: "Médio", value: -28000  },
  { name: "Vista",        impact: "Baixo", value: +15000  },
]

// Esses valores vêm de shap_contributions no PredictionResponse
// Cada valor = quanto aquela feature deslocou o preço base
```

O badge de impacto é calculado pelo valor absoluto do SHAP:
- `|shap| > $100k` → Alto (verde/vermelho)
- `|shap| > $30k` → Médio (amarelo)
- resto → Baixo (cinza)

**Link "Ver análise completa"** → abre modal ou expande com todas as features.

#### 4.2 — "Contexto de Mercado" (MarketContext)

```tsx
// components/prediction/MarketContext.tsx

// Tabela superior:
// Mediana | Faixa Interquartil | Imóveis similares
// $550k   | $500k-$720k        | 24 encontrados

// Gráfico inferior: bell curve aproximada com Recharts AreaChart
// Área = distribuição de preços do zipcode (P25 a P75)
// Linha vertical = preço previsto ("Você")

const MarketContext = ({ prediction, percentiles, similarCount }) => {
  // Gerar curva aproximada a partir dos percentis
  const curveData = generateBellCurve(percentiles.p25, percentiles.p50, percentiles.p75)

  return (
    <Card>
      <CardHeader>
        <CardTitle>Contexto de Mercado</CardTitle>
        <p>Comparação com imóveis no zipcode {prediction.zipcode}</p>
      </CardHeader>
      <CardContent>
        <MarketStatsRow {...percentiles} similarCount={similarCount} />
        <AreaChart data={curveData} height={150}>
          <Area dataKey="density" fill="#6366f1" fillOpacity={0.3} stroke="#6366f1" />
          <ReferenceLine x={prediction.predicted_price} label="Você" stroke="#7c3aed" />
        </AreaChart>
      </CardContent>
    </Card>
  )
}
```

**Gerar a curva:** Uma curva normal aproximada com `mean=p50`, `std=(p75-p25)/1.35`
pode ser gerada matematicamente no frontend sem precisar de dados extras.

#### 4.3 — FeatureImportance (barras horizontais)

```tsx
// components/prediction/FeatureImportance.tsx
// Recharts BarChart horizontal com top_features do PredictionResponse

const FeatureImportance = ({ features }) => (
  <Card>
    <CardHeader>
      <CardTitle>Fatores que mais influenciam</CardTitle>
      <p className="text-sm text-muted-foreground">
        Importância das variáveis no modelo (XGBoost)
      </p>
    </CardHeader>
    <CardContent>
      <BarChart layout="vertical" data={chartData} height={200}>
        <XAxis type="number" tickFormatter={(v) => `${(v*100).toFixed(0)}%`} />
        <YAxis type="category" dataKey="name" width={100} />
        <Bar dataKey="importance" fill="#6366f1" radius={[0, 4, 4, 0]} />
      </BarChart>
    </CardContent>
  </Card>
)
```

#### 4.4 — Warnings (Pontos de Atenção)

```tsx
// components/prediction/Warnings.tsx
// Lista de warnings com ícones coloridos

const ICONS = {
  warning: AlertTriangle,   // amarelo
  info:    Info,            // azul
  success: CheckCircle,     // verde
}

const Warnings = ({ warnings }) => (
  <Card>
    <CardHeader><CardTitle>Pontos de atenção</CardTitle></CardHeader>
    <CardContent>
      <ul className="space-y-2">
        {warnings.map((w, i) => (
          <li key={i} className="flex items-start gap-2 text-sm">
            <AlertTriangle className="text-yellow-500 shrink-0 mt-0.5" size={16} />
            {w}
          </li>
        ))}
      </ul>
    </CardContent>
  </Card>
)
```

**Tempo estimado da Fase 4: 6–8 horas**

---

### FASE 5 — Chat panel

**Objetivo:** Painel direito com chat melhorado.

#### 5.1 — ChatPanel layout

```tsx
// components/layout/ChatPanel.tsx
const ChatPanel = () => (
  <aside className="flex flex-col h-full border-l bg-background">
    {/* Header */}
    <div className="p-4 border-b flex justify-between items-center">
      <div className="flex items-center gap-2">
        <Bot size={18} className="text-violet-500" />
        <span className="font-semibold">Assistente IA</span>
      </div>
      <Button variant="ghost" size="sm" onClick={clearChat}>
        <RotateCcw size={14} /> Limpar chat
      </Button>
    </div>

    {/* Mensagens */}
    <div className="flex-1 overflow-y-auto p-4 space-y-3" ref={scrollRef}>
      <WelcomeMessage />
      {messages.map((msg) => <ChatBubble key={msg.id} message={msg} />)}
      {isLoading && <TypingIndicator />}
    </div>

    {/* Footer */}
    <div className="p-4 border-t">
      <ChatInput onSend={handleSend} disabled={isLoading} />
      <p className="text-xs text-muted-foreground text-center mt-2">
        As respostas podem conter imprecisões. Sempre valide informações importantes.
      </p>
    </div>
  </aside>
)
```

#### 5.2 — ChatBubble com thumbs up/down

```tsx
// Mensagens do usuário: bubble direita, fundo roxo
// Mensagens do assistente: bubble esquerda, fundo cinza + thumbs up/down

const ChatBubble = ({ message }) => {
  const isUser = message.role === "user"

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      {!isUser && <Bot size={24} className="shrink-0 mr-2 text-violet-500" />}
      <div className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm
        ${isUser
          ? "bg-violet-600 text-white rounded-br-sm"
          : "bg-muted rounded-bl-sm"
        }`}>
        {message.content}
        {!isUser && (
          <div className="flex gap-2 mt-2 pt-2 border-t border-border/30">
            <Button variant="ghost" size="icon" className="h-6 w-6">
              <ThumbsUp size={12} />
            </Button>
            <Button variant="ghost" size="icon" className="h-6 w-6">
              <ThumbsDown size={12} />
            </Button>
          </div>
        )}
      </div>
    </div>
  )
}
```

#### 5.3 — ChatInput com envio por Enter

```tsx
const ChatInput = ({ onSend, disabled }) => {
  const [value, setValue] = useState("")

  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      onSend(value)
      setValue("")
    }
  }

  return (
    <div className="flex gap-2">
      <Textarea
        placeholder="Digite sua pergunta..."
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        rows={1}
        className="resize-none"
      />
      <Button onClick={() => onSend(value)} disabled={disabled || !value.trim()}>
        <Send size={16} />
      </Button>
    </div>
  )
}
```

**Tempo estimado da Fase 5: 4–5 horas**

---

### FASE 6 — Header, dark mode e export

**Objetivo:** Header com ações globais e toggle de tema.

#### 6.1 — Header

```tsx
// components/layout/Header.tsx
const Header = () => (
  <header className="flex items-center justify-between px-6 py-4 border-b">
    <div>
      <h1 className="text-2xl font-bold">Olá! 👋</h1>
      <p className="text-muted-foreground text-sm">
        Descubra o valor estimado e insights inteligentes para qualquer imóvel.
      </p>
    </div>
    <div className="flex items-center gap-3">
      <Button variant="outline" onClick={exportPDF}>
        <Download size={14} className="mr-2" />
        Exportar
      </Button>
      <Button variant="ghost">Sobre</Button>
      <ThemeToggle />
      <Avatar initials="DS" />
    </div>
  </header>
)
```

#### 6.2 — Dark mode com CSS variables + Zustand

Sem `next-themes` — o Vite não tem `layout.tsx`. Basta alternar a classe `dark`
no `<html>` manualmente e persistir em `localStorage`.

```tsx
// src/hooks/useTheme.ts
import { useEffect, useState } from 'react'

export function useTheme() {
  const [isDark, setIsDark] = useState(
    () => localStorage.getItem('theme') === 'dark'
  )

  useEffect(() => {
    document.documentElement.classList.toggle('dark', isDark)
    localStorage.setItem('theme', isDark ? 'dark' : 'light')
  }, [isDark])

  return { isDark, toggle: () => setIsDark((v) => !v) }
}
```

```tsx
// src/App.tsx — aplicar tema na montagem
useEffect(() => {
  const saved = localStorage.getItem('theme') ?? 'dark'
  document.documentElement.classList.toggle('dark', saved === 'dark')
}, [])
```

#### 6.3 — Export PDF/PNG (opcional)

```tsx
// lib/export.ts
// Usa html2canvas + jsPDF para gerar PDF com o resultado da predição

import html2canvas from "html2canvas"
import jsPDF from "jspdf"

export async function exportToPDF(elementId: string) {
  const element = document.getElementById(elementId)
  const canvas = await html2canvas(element)
  const pdf = new jsPDF()
  pdf.addImage(canvas.toDataURL(), "PNG", 10, 10, 190, 0)
  pdf.save("previsao-madeinweb-teste.pdf")
}
```

**Tempo estimado da Fase 6: 2–3 horas**

---

### FASE 7 — Integração final e polish

**Objetivo:** Tudo conectado, responsivo e polished.

#### 7.1 — Zustand store (estado global)

```tsx
// src/store/usePredictionStore.ts
interface PredictionStore {
  prediction: PredictionResponse | null
  isLoading: boolean
  error: string | null
  submitPrediction: (input: HouseInput) => Promise<void>
  clearPrediction: () => void
}

export const usePredictionStore = create<PredictionStore>((set) => ({
  prediction: null,
  isLoading: false,
  error: null,
  submitPrediction: async (input) => {
    set({ isLoading: true, error: null })
    try {
      const result = await api.predict(input)
      set({ prediction: result, isLoading: false })
    } catch (err) {
      set({ error: err.message, isLoading: false })
    }
  },
  clearPrediction: () => set({ prediction: null }),
}))
```

#### 7.2 — Tela de boas-vindas (sem predição ativa)

```tsx
// Exibida no lugar dos cards quando prediction === null
const WelcomeState = () => (
  <div className="flex flex-col items-center justify-center h-full text-center p-8">
    <div className="w-16 h-16 rounded-full bg-violet-500/10 flex items-center justify-center mb-4">
      <Home size={32} className="text-violet-500" />
    </div>
    <h2 className="text-xl font-semibold mb-2">Pronto para avaliar</h2>
    <p className="text-muted-foreground max-w-sm">
      Preencha os dados do imóvel no painel esquerdo e clique em
      <strong> Prever Preço</strong> para ver a análise completa.
    </p>
    <div className="grid grid-cols-3 gap-4 mt-8 w-full max-w-sm">
      <FeatureHighlight icon={Brain}   label="XGBoost"    sub="R² ≈ 0.89" />
      <FeatureHighlight icon={Search}  label="RAG"        sub="5 fontes" />
      <FeatureHighlight icon={MessageCircle} label="Chat" sub="GPT-4o" />
    </div>
  </div>
)
```

#### 7.3 — Skeleton loading

```tsx
// Exibido enquanto a API está sendo chamada
const PredictionSkeleton = () => (
  <div className="space-y-4">
    <Skeleton className="h-36 w-full rounded-2xl" />  {/* PriceCard */}
    <div className="grid grid-cols-5 gap-2">
      {[...Array(5)].map((_, i) => <Skeleton key={i} className="h-16" />)}
    </div>
    <div className="grid grid-cols-2 gap-4">
      <Skeleton className="h-48" />
      <Skeleton className="h-48" />
    </div>
  </div>
)
```

#### 7.4 — Responsividade

O layout 3 colunas colapsa progressivamente:
- `> 1280px`: 3 colunas (sidebar + main + chat)
- `768–1280px`: sidebar recolhida (Sheet drawer) + main + chat como tab
- `< 768px`: mobile com navegação por tabs (Formulário | Resultado | Chat)

**Tempo estimado da Fase 7: 4–6 horas**

---

## Mudanças no docker-compose.yml

```yaml
# Adicionar o serviço do frontend
services:
  api:
    build: .
    ports: ["8001:8001"]

  frontend:
    build: ./frontend
    ports: ["5173:5173"]
    environment:
      - VITE_API_URL=http://api:8001
    depends_on: [api]
```

**Dockerfile do frontend:**
```dockerfile
# frontend/Dockerfile
FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host"]
```

---

## Resumo de esforço

| Fase | O que faz | Estimativa |
|---|---|---|
| 0 | Backend: SHAP por predição, confidence, percentis, warnings | 4–6h |
| 1 | Setup Next.js + shadcn/ui + estrutura de pastas | 2–3h |
| 2 | Layout 3 colunas + sidebar completa | 4–6h |
| 3 | PriceCard + ConfidenceGauge + PropertySummary | 4–5h |
| 4 | WhyThisPrice + MarketContext + FeatureImportance + Warnings | 6–8h |
| 5 | Chat panel com bubbles + thumbs up/down | 4–5h |
| 6 | Header + dark mode + export | 2–3h |
| 7 | Integração final + skeletons + responsividade | 4–6h |
| **Total** | | **30–42 horas** |

---

## Ordem recomendada de execução

```
Fase 0 → Fase 1 → Fase 2 → Fase 3 → Fase 5 → Fase 4 → Fase 6 → Fase 7
```

Motivo: fazer o chat funcionar (Fase 5) antes dos cards analíticos (Fase 4) garante
que você tenha uma demo funcional mais cedo, mesmo que alguns cards estejam faltando.

---

## Dependências NPM completas

```json
{
  "dependencies": {
    "react": "^18.x",
    "react-dom": "^18.x",
    "recharts": "^2.x",
    "zustand": "^4.x",
    "axios": "^1.x",
    "lucide-react": "latest",
    "html2canvas": "^1.x",
    "jspdf": "^2.x",
    "@radix-ui/react-slider": "latest",
    "@radix-ui/react-collapsible": "latest",
    "@radix-ui/react-avatar": "latest",
    "clsx": "latest",
    "tailwind-merge": "latest",
    "class-variance-authority": "latest"
  },
  "devDependencies": {
    "vite": "^5.x",
    "@vitejs/plugin-react": "^4.x",
    "typescript": "^5.x",
    "tailwindcss": "^3.x",
    "postcss": "^8.x",
    "autoprefixer": "^10.x",
    "@types/react": "^18.x",
    "@types/react-dom": "^18.x",
    "@types/node": "^20.x"
  }
}
```

---

## O que NÃO muda

- Toda a pasta `app/` (FastAPI, ML, RAG, DB) permanece igual
- `app/ui/streamlit_app.py` pode continuar existindo como fallback
- `requirements.txt` não precisa de nada novo para as fases 1–7
- O Makefile ganha apenas `make frontend` e `make dev` (API + frontend em paralelo)
