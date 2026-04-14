import { useRef, useEffect, useState } from 'react'
import { useChat } from '@/hooks/useChat'
import { usePredictionStore } from '@/store/usePredictionStore'
import {
  Send,
  Bot,
  User,
  RotateCcw,
  ThumbsUp,
  ThumbsDown,
  Sparkles,
  X,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import type { ChatMessage } from '@/types/prediction'

// ── Sugestões de perguntas ─────────────────────────────────────────────────────
const SUGGESTIONS_WITH_PREDICTION = [
  'Por que esse preço foi estimado?',
  'Quais reformas aumentariam mais o valor?',
  'Como a localização afeta o preço?',
  'O imóvel está acima ou abaixo do mercado?',
]

const SUGGESTIONS_DEFAULT = [
  'O que é o grade de um imóvel?',
  'Como funciona o modelo de previsão?',
  'Quais fatores mais afetam o preço?',
]

interface ChatPanelProps {
  onClose?: () => void
}

export function ChatPanel({ onClose }: ChatPanelProps) {
  const { messages, sendMessage, clearChat, isChatLoading } = useChat()
  const hasPrediction = usePredictionStore((s) => s.result !== null)
  const [draft, setDraft] = useState('')
  const [ratings, setRatings] = useState<Record<number, 'up' | 'down' | null>>({})
  const bottomRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // Auto-scroll para o final ao receber nova mensagem
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isChatLoading])

  // Auto-resize do textarea
  useEffect(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 120)}px`
  }, [draft])

  function handleSend(text = draft) {
    const trimmed = text.trim()
    if (!trimmed || isChatLoading) return
    sendMessage(trimmed)
    setDraft('')
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  function toggleRating(index: number, rating: 'up' | 'down') {
    setRatings((prev) => ({
      ...prev,
      [index]: prev[index] === rating ? null : rating,
    }))
  }

  const suggestions = hasPrediction ? SUGGESTIONS_WITH_PREDICTION : SUGGESTIONS_DEFAULT

  return (
    <aside className="flex w-88 shrink-0 flex-col border-l border-border bg-card" style={{ width: '22rem' }}>

      {/* ── Header ── */}
      <div className="flex h-14 items-center justify-between border-b border-border px-4 shrink-0">
        <div className="flex items-center gap-2">
          {onClose && (
            <button
              onClick={onClose}
              className="flex h-7 w-7 items-center justify-center rounded-lg text-muted-foreground hover:bg-muted hover:text-foreground transition-colors mr-1"
              aria-label="Fechar chat"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          )}
          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-primary/10">
            <Bot className="h-3.5 w-3.5 text-primary" />
          </div>
          <span className="text-sm font-semibold text-foreground">Assistente IA</span>
        </div>

        {messages.length > 0 && (
          <button
            onClick={clearChat}
            className="flex items-center gap-1.5 rounded-lg px-2 py-1 text-xs text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
          >
            <RotateCcw className="h-3 w-3" />
            Limpar
          </button>
        )}
      </div>

      {/* ── Mensagens ── */}
      <div className="flex-1 overflow-y-auto px-3 py-3 space-y-3">

        {/* Welcome state */}
        {messages.length === 0 && (
          <WelcomeMessage
            suggestions={suggestions}
            onSuggest={handleSend}
          />
        )}

        {/* Mensagens */}
        {messages.map((msg, i) => (
          <ChatBubble
            key={i}
            message={msg}
            rating={ratings[i] ?? null}
            onRate={(r) => toggleRating(i, r)}
          />
        ))}

        {/* Typing indicator */}
        {isChatLoading && <TypingIndicator />}

        <div ref={bottomRef} />
      </div>

      {/* ── Input ── */}
      <div className="border-t border-border p-3 space-y-2">
        <div className="flex items-end gap-2 rounded-xl border border-border bg-background px-3 py-2 focus-within:ring-1 focus-within:ring-ring transition-shadow">
          <textarea
            ref={textareaRef}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Pergunte sobre o imóvel…"
            rows={1}
            className="flex-1 resize-none bg-transparent text-sm text-foreground placeholder:text-muted-foreground focus:outline-none max-h-28 leading-relaxed"
          />
          <button
            onClick={() => handleSend()}
            disabled={!draft.trim() || isChatLoading}
            className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground transition-all hover:opacity-90 disabled:opacity-40 active:scale-95"
          >
            <Send className="h-3.5 w-3.5" />
          </button>
        </div>

        <p className="text-center text-[10px] text-muted-foreground leading-relaxed px-1">
          As respostas podem conter imprecisões. Sempre valide informações importantes.
        </p>
      </div>
    </aside>
  )
}

/* ── Welcome message ── */
function WelcomeMessage({
  suggestions,
  onSuggest,
}: {
  suggestions: string[]
  onSuggest: (text: string) => void
}) {
  return (
    <div className="flex flex-col items-center gap-4 py-6 text-center">
      <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-primary/10">
        <Sparkles className="h-6 w-6 text-primary" />
      </div>

      <div className="space-y-1">
        <p className="text-sm font-semibold text-foreground">Assistente de Imóveis</p>
        <p className="text-xs text-muted-foreground leading-relaxed max-w-[220px]">
          Tire dúvidas sobre o imóvel, o mercado ou o modelo de previsão.
        </p>
      </div>

      <div className="w-full space-y-1.5">
        {suggestions.map((s) => (
          <button
            key={s}
            onClick={() => onSuggest(s)}
            className="w-full rounded-lg border border-border bg-background px-3 py-2 text-left text-xs text-foreground transition-colors hover:bg-muted hover:border-primary/30"
          >
            {s}
          </button>
        ))}
      </div>
    </div>
  )
}

/* ── ChatBubble ── */
function ChatBubble({
  message,
  rating,
  onRate,
}: {
  message: ChatMessage
  rating: 'up' | 'down' | null
  onRate: (r: 'up' | 'down') => void
}) {
  const isUser = message.role === 'user'

  return (
    <div className={cn('flex gap-2', isUser ? 'justify-end' : 'justify-start')}>
      {/* Avatar do assistente */}
      {!isUser && (
        <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary/10 mt-1">
          <Bot className="h-3.5 w-3.5 text-primary" />
        </div>
      )}

      <div className="flex flex-col gap-1 max-w-[85%]">
        {/* Bubble */}
        <div
          className={cn(
            'rounded-2xl px-3 py-2 text-sm leading-relaxed',
            isUser
              ? 'bg-primary text-primary-foreground rounded-tr-sm'
              : 'bg-muted text-foreground rounded-tl-sm',
          )}
        >
          {message.content}
        </div>

        {/* Thumbs up/down — apenas respostas do assistente */}
        {!isUser && (
          <div className="flex items-center gap-1 ml-1">
            <RatingButton
              icon={ThumbsUp}
              active={rating === 'up'}
              activeClass="text-emerald-500"
              onClick={() => onRate('up')}
              label="Útil"
            />
            <RatingButton
              icon={ThumbsDown}
              active={rating === 'down'}
              activeClass="text-red-500"
              onClick={() => onRate('down')}
              label="Não útil"
            />
          </div>
        )}
      </div>

      {/* Avatar do usuário */}
      {isUser && (
        <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-secondary mt-1">
          <User className="h-3.5 w-3.5 text-secondary-foreground" />
        </div>
      )}
    </div>
  )
}

/* ── RatingButton ── */
function RatingButton({
  icon: Icon,
  active,
  activeClass,
  onClick,
  label,
}: {
  icon: React.ElementType
  active: boolean
  activeClass: string
  onClick: () => void
  label: string
}) {
  return (
    <button
      onClick={onClick}
      aria-label={label}
      className={cn(
        'flex h-5 w-5 items-center justify-center rounded-md transition-colors hover:bg-muted',
        active ? activeClass : 'text-muted-foreground',
      )}
    >
      <Icon className="h-3 w-3" />
    </button>
  )
}

/* ── Typing indicator com 3 pontos ── */
function TypingIndicator() {
  return (
    <div className="flex items-center gap-2">
      <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary/10">
        <Bot className="h-3.5 w-3.5 text-primary" />
      </div>
      <div className="flex items-center gap-1.5 rounded-2xl rounded-tl-sm bg-muted px-3 py-2.5">
        <span className="typing-dot" style={{ animationDelay: '0ms' }} />
        <span className="typing-dot" style={{ animationDelay: '160ms' }} />
        <span className="typing-dot" style={{ animationDelay: '320ms' }} />
      </div>
    </div>
  )
}
