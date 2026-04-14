import { useEffect, useState } from 'react'
import { SlidersHorizontal, BarChart3, MessageCircle } from 'lucide-react'
import { Sidebar } from '@/components/layout/Sidebar'
import { Header } from '@/components/layout/Header'
import { ChatPanel } from '@/components/layout/ChatPanel'
import { MainContent } from '@/components/layout/MainContent'
import { useTheme } from '@/hooks/useTheme'
import { cn } from '@/lib/utils'

type MobileTab = 'form' | 'result' | 'chat'

export default function App() {
  // Chama o hook para registrar o useEffect que mantém o <html> sincronizado.
  // O estado real vive no Zustand — não precisa de useEffect local aqui.
  useTheme()

  useEffect(() => {
    document.title = 'Demetrio — madeinweb'
  }, [])

  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [chatOpen, setChatOpen]     = useState(false)
  const [mobileTab, setMobileTab]   = useState<MobileTab>('result')

  // Fecha overlays ao redimensionar para desktop
  useEffect(() => {
    function onResize() {
      if (window.innerWidth >= 1280) {
        setSidebarOpen(false)
        setChatOpen(false)
      }
    }
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [])

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-background">

      {/* ════════════════════════════════════════════
          SIDEBAR
          • xl+   → coluna estática sempre visível
          • <xl   → overlay deslizante (sidebarOpen)
          • <md   → tab "Formulário" no bottom bar
      ════════════════════════════════════════════ */}

      {/* Estática — desktop */}
      <div className="hidden xl:flex shrink-0">
        <Sidebar />
      </div>

      {/* Overlay — tablet / laptop */}
      {sidebarOpen && (
        <div className="xl:hidden">
          <div
            className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm"
            onClick={() => setSidebarOpen(false)}
          />
          <div className="fixed inset-y-0 left-0 z-50 shadow-2xl animate-in slide-in-from-left duration-300">
            <Sidebar onClose={() => setSidebarOpen(false)} />
          </div>
        </div>
      )}

      {/* Tab "Formulário" — mobile apenas */}
      <div
        className={cn(
          'flex-col overflow-hidden flex-1 min-w-0',
          mobileTab === 'form' ? 'flex md:hidden' : 'hidden',
        )}
      >
        {/* Override do w-72 para preencher a tela no mobile */}
        <div className="flex flex-1 flex-col overflow-hidden [&>aside]:w-full [&>aside]:border-r-0">
          <Sidebar />
        </div>
      </div>

      {/* ════════════════════════════════════════════
          CONTEÚDO PRINCIPAL
          • Sempre visível em md+
          • Mobile: só quando mobileTab === 'result'
      ════════════════════════════════════════════ */}
      <div
        className={cn(
          'flex flex-1 flex-col overflow-hidden min-w-0',
          mobileTab !== 'result' ? 'hidden md:flex' : 'flex',
        )}
      >
        <Header
          onMenuClick={() => setSidebarOpen((v) => !v)}
          onChatClick={() => setChatOpen((v) => !v)}
        />
        {/* pb-16 no mobile para não sobrepor o tab bar */}
        <main className="flex-1 overflow-y-auto px-4 py-4 md:p-6 pb-16 md:pb-6">
          <MainContent />
        </main>
      </div>

      {/* ════════════════════════════════════════════
          CHAT PANEL
          • xl+   → coluna estática sempre visível
          • md-xl → overlay deslizante (chatOpen)
          • <md   → tab "Chat" no bottom bar
      ════════════════════════════════════════════ */}

      {/* Estático — desktop */}
      <div className="hidden xl:flex shrink-0">
        <ChatPanel />
      </div>

      {/* Overlay — tablet / laptop */}
      {chatOpen && (
        <div className="hidden md:block xl:hidden">
          <div
            className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm"
            onClick={() => setChatOpen(false)}
          />
          <div className="fixed inset-y-0 right-0 z-50 shadow-2xl animate-in slide-in-from-right duration-300">
            <ChatPanel onClose={() => setChatOpen(false)} />
          </div>
        </div>
      )}

      {/* Tab "Chat" — mobile apenas */}
      <div
        className={cn(
          'flex-col overflow-hidden flex-1 min-w-0',
          mobileTab === 'chat' ? 'flex md:hidden' : 'hidden',
        )}
      >
        <div className="flex flex-1 flex-col overflow-hidden [&>aside]:w-full [&>aside]:border-l-0">
          <ChatPanel />
        </div>
      </div>

      {/* ════════════════════════════════════════════
          BOTTOM TAB BAR — apenas mobile (<md)
      ════════════════════════════════════════════ */}
      <nav className="fixed bottom-0 left-0 right-0 z-30 flex border-t border-border bg-card/95 backdrop-blur-sm md:hidden">
        <MobileTab
          icon={SlidersHorizontal}
          label="Formulário"
          active={mobileTab === 'form'}
          onClick={() => setMobileTab('form')}
        />
        <MobileTab
          icon={BarChart3}
          label="Resultado"
          active={mobileTab === 'result'}
          onClick={() => setMobileTab('result')}
        />
        <MobileTab
          icon={MessageCircle}
          label="Chat"
          active={mobileTab === 'chat'}
          onClick={() => setMobileTab('chat')}
        />
      </nav>
    </div>
  )
}

/* ── Mobile tab button ── */
function MobileTab({
  icon: Icon,
  label,
  active,
  onClick,
}: {
  icon: React.ElementType
  label: string
  active: boolean
  onClick: () => void
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'flex flex-1 flex-col items-center justify-center gap-0.5 py-2.5 text-[10px] font-medium transition-colors',
        active ? 'text-primary' : 'text-muted-foreground hover:text-foreground',
      )}
    >
      <Icon className="h-5 w-5" />
      {label}
    </button>
  )
}
