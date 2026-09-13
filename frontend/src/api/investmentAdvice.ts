import type {
  InvestmentAdviceHistoryResponse,
  InvestmentAdviceResponse,
} from '../types/investmentAdvice'

async function readErrorDetail(response: Response, fallbackMessage: string): Promise<Error> {
  try {
    const payload = (await response.json()) as { detail?: string }
    if (typeof payload.detail === 'string' && payload.detail.trim()) {
      return new Error(payload.detail)
    }
  } catch {
    // ignore JSON parse failures and fall back to the generic message
  }

  return new Error(fallbackMessage)
}

export async function generateStockAdvice(securityId: number, useCache = true): Promise<InvestmentAdviceResponse> {
  const response = await fetch(`/api/ai/stocks/${securityId}/advice?use_cache=${useCache ? 'true' : 'false'}`, {
    method: 'POST',
  })

  if (!response.ok) {
    throw await readErrorDetail(response, 'Unable to generate stock advice right now.')
  }

  return (await response.json()) as InvestmentAdviceResponse
}

export async function generateHoldingAdvice(holdingId: number, useCache = true): Promise<InvestmentAdviceResponse> {
  const response = await fetch(`/api/ai/holdings/${holdingId}/advice?use_cache=${useCache ? 'true' : 'false'}`, {
    method: 'POST',
  })

  if (!response.ok) {
    throw await readErrorDetail(response, 'Unable to generate holding advice right now.')
  }

  return (await response.json()) as InvestmentAdviceResponse
}

export async function fetchInvestmentAdviceHistory(): Promise<InvestmentAdviceHistoryResponse> {
  const response = await fetch('/api/ai/history')

  if (!response.ok) {
    throw await readErrorDetail(response, 'Unable to load advice history right now.')
  }

  return (await response.json()) as InvestmentAdviceHistoryResponse
}
