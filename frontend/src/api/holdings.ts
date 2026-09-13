import type {
  HoldingRemoveResponse,
  HoldingResponse,
  HoldingUpsertRequest,
} from '../types/holdings'

export async function fetchHoldings(): Promise<HoldingResponse[]> {
  const response = await fetch('/api/holdings')

  if (!response.ok) {
    throw new Error('Unable to load holdings right now.')
  }

  return (await response.json()) as HoldingResponse[]
}

export async function upsertHolding(payload: HoldingUpsertRequest): Promise<HoldingResponse> {
  const response = await fetch('/api/holdings', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })

  if (!response.ok) {
    throw new Error('Unable to save holding right now.')
  }

  return (await response.json()) as HoldingResponse
}

export async function updateHolding(
  holdingId: number,
  payload: HoldingUpsertRequest,
): Promise<HoldingResponse> {
  const response = await fetch(`/api/holdings/${holdingId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })

  if (!response.ok) {
    throw new Error('Unable to update holding right now.')
  }

  return (await response.json()) as HoldingResponse
}

export async function removeHolding(holdingId: number): Promise<HoldingRemoveResponse> {
  const response = await fetch(`/api/holdings/${holdingId}`, {
    method: 'DELETE',
  })

  if (!response.ok) {
    throw new Error('Unable to remove holding right now.')
  }

  return (await response.json()) as HoldingRemoveResponse
}
