import axios from 'axios'
import type { HouseInput, PredictionResponse, ChatRequest, ChatResponse } from '@/types/prediction'

const http = axios.create({
  baseURL: '/api',
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
