import { usePredictionStore } from '@/store/usePredictionStore'
import { predict } from '@/lib/api'

export function usePrediction() {
  const { input, setInput, result, isLoading, error, setResult, setLoading, setError } =
    usePredictionStore()

  async function submit() {
    setLoading(true)
    setError(null)
    try {
      const res = await predict(input)
      setResult(res)
    } catch (e: unknown) {
      const msg =
        e instanceof Error ? e.message : 'Erro ao obter previsão. Tente novamente.'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  return { input, setInput, result, isLoading, error, submit }
}
