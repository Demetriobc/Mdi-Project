import { usePredictionStore } from '@/store/usePredictionStore'
import { chat } from '@/lib/api'
import type { PredictionContext } from '@/types/prediction'

export function useChat() {
  const { messages, addMessage, isChatLoading, setChatLoading, result } =
    usePredictionStore()

  async function sendMessage(text: string) {
    if (!text.trim() || isChatLoading) return

    addMessage({ role: 'user', content: text })
    setChatLoading(true)

    const context: PredictionContext | null = result
      ? {
          predicted_price: result.predicted_price,
          predicted_price_formatted: result.predicted_price_formatted,
          zipcode: result.zipcode,
          sqft_living: result.sqft_living,
          bedrooms: result.bedrooms,
          bathrooms: result.bathrooms,
          grade: result.grade,
          condition: result.condition,
          top_features: result.top_features,
          zipcode_median_price: result.zipcode_median_price,
          price_vs_median_pct: result.price_vs_median_pct,
        }
      : null

    try {
      const res = await chat({
        message: text,
        prediction_context: context,
        conversation_history: messages,
      })
      addMessage({ role: 'assistant', content: res.answer })
    } catch {
      addMessage({
        role: 'assistant',
        content: 'Desculpe, ocorreu um erro ao processar sua mensagem.',
      })
    } finally {
      setChatLoading(false)
    }
  }

  function clearChat() {
    usePredictionStore.getState().clearMessages()
  }

  return { messages, sendMessage, clearChat, isChatLoading }
}
