import { create } from 'zustand'
import type { HouseInput, PredictionResponse, ChatMessage } from '@/types/prediction'

interface PredictionState {
  // Form
  input: HouseInput
  setInput: (patch: Partial<HouseInput>) => void

  // Prediction result
  result: PredictionResponse | null
  isLoading: boolean
  error: string | null
  setResult: (r: PredictionResponse) => void
  setLoading: (v: boolean) => void
  setError: (e: string | null) => void

  // Chat
  messages: ChatMessage[]
  addMessage: (m: ChatMessage) => void
  clearMessages: () => void
  isChatLoading: boolean
  setChatLoading: (v: boolean) => void
}

const defaultInput: HouseInput = {
  bedrooms: 3,
  bathrooms: 2,
  sqft_living: 1800,
  sqft_lot: 5000,
  floors: 1,
  waterfront: 0,
  view: 0,
  condition: 3,
  grade: 7,
  sqft_above: 1800,
  sqft_basement: 0,
  yr_built: 2000,
  yr_renovated: 0,
  zipcode: '98103',
  lat: 47.6101,
  long: -122.3420,
  sqft_living15: 1800,
  sqft_lot15: 5000,
}

export const usePredictionStore = create<PredictionState>((set) => ({
  input: defaultInput,
  setInput: (patch) =>
    set((s) => ({ input: { ...s.input, ...patch } })),

  result: null,
  isLoading: false,
  error: null,
  setResult: (result) => set({ result, error: null }),
  setLoading: (isLoading) => set({ isLoading }),
  setError: (error) => set({ error }),

  messages: [],
  addMessage: (m) => set((s) => ({ messages: [...s.messages, m] })),
  clearMessages: () => set({ messages: [] }),
  isChatLoading: false,
  setChatLoading: (isChatLoading) => set({ isChatLoading }),
}))
