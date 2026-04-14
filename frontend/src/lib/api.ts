import axios from 'axios'
import type { HouseInput, PredictionResponse, ChatRequest, ChatResponse } from '@/types/prediction'

/**
 * Produção (Railway, etc.): defina VITE_API_BASE_URL=https://sua-api.up.railway.app
 * Dev: omita — o Vite proxy usa baseURL /api → localhost:8001
 */
const apiRoot = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, '') ?? ''
const baseURL = apiRoot.length > 0 ? apiRoot : '/api'

const http = axios.create({
  baseURL,
  timeout: 60_000,
})

export async function predict(input: HouseInput): Promise<PredictionResponse> {
  const { data } = await http.post<PredictionResponse>('/predict', input)
  return data
}

export async function chat(payload: ChatRequest): Promise<ChatResponse> {
  const { data } = await http.post<ChatResponse>('/chat', payload)
  return data
}

export async function healthCheck(): Promise<{ status: string }> {
  const { data } = await http.get('/health')
  return data
}
