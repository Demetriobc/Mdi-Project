import { create } from 'zustand'

function readDefaultRate(): number {
  const raw = import.meta.env.VITE_USD_BRL_RATE
  const n = raw != null && raw !== '' ? Number(raw) : NaN
  return Number.isFinite(n) && n > 0 ? n : 5.5
}

interface CurrencyDisplayState {
  /** Mostrar conversão aproximada em R$ ao lado dos valores em US$ */
  showBrlParallel: boolean
  /** Quantos R$ por 1 US$ (referência; ajuste conforme cotação do dia) */
  usdToBrl: number
  setShowBrlParallel: (v: boolean) => void
  setUsdToBrl: (v: number) => void
}

export const useCurrencyDisplayStore = create<CurrencyDisplayState>((set) => ({
  showBrlParallel: false,
  usdToBrl: readDefaultRate(),
  setShowBrlParallel: (showBrlParallel) => set({ showBrlParallel }),
  setUsdToBrl: (usdToBrl) => set({ usdToBrl: Math.max(0.01, usdToBrl) }),
}))
