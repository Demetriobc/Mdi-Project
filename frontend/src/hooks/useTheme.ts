import { useEffect } from 'react'
import { create } from 'zustand'

interface ThemeState {
  isDark: boolean
  toggle: () => void
}

// Zustand garante estado singleton — todos os componentes que chamam
// useTheme() compartilham a mesma instância, sem problema de instâncias separadas.
const useThemeStore = create<ThemeState>((set) => ({
  isDark: (() => {
    try { return (localStorage.getItem('theme') ?? 'dark') === 'dark' } catch { return true }
  })(),
  toggle: () => set((s) => ({ isDark: !s.isDark })),
}))

export function useTheme() {
  const { isDark, toggle } = useThemeStore()

  // O efeito fica aqui — qualquer componente que chame toggle()
  // dispara este useEffect e aplica a classe no <html>.
  useEffect(() => {
    document.documentElement.classList.toggle('dark', isDark)
    localStorage.setItem('theme', isDark ? 'dark' : 'light')
  }, [isDark])

  return { isDark, toggle }
}
