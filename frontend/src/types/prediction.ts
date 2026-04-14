// Espelha os schemas Pydantic do backend (app/api/schemas/prediction.py e chat.py)

export interface HouseInput {
  bedrooms: number
  bathrooms: number
  sqft_living: number
  sqft_lot: number
  floors: number
  waterfront: number
  view: number
  condition: number
  grade: number
  sqft_above: number
  sqft_basement: number
  yr_built: number
  yr_renovated: number
  zipcode: string
  lat: number
  long: number
  sqft_living15: number
  sqft_lot15: number
}

export interface PredictionResponse {
  predicted_price: number
  predicted_price_formatted: string
  zipcode: string
  sqft_living: number
  bedrooms: number
  bathrooms: number
  grade: number
  condition: number
  zipcode_median_price: number | null
  price_vs_median_pct: number | null
  price_p10: number | null
  price_p90: number | null
  model_version: string
  top_features: Record<string, number>
  // Campos que serão adicionados na Fase 0
  shap_contributions?: Record<string, number>
  confidence?: { score: number; label: string; color: string }
  market_percentiles?: { p25: number; p50: number; p75: number }
  warnings?: string[]
  similar_count?: number
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

export interface PredictionContext {
  predicted_price: number
  predicted_price_formatted: string
  zipcode: string
  sqft_living: number
  bedrooms: number
  bathrooms: number
  grade: number
  condition: number
  top_features: Record<string, number>
  zipcode_median_price: number | null
  price_vs_median_pct: number | null
}

export interface ChatRequest {
  message: string
  prediction_context: PredictionContext | null
  conversation_history: ChatMessage[]
}

export interface ChatResponse {
  answer: string
  sources: string[]
  llm_available: boolean
}
