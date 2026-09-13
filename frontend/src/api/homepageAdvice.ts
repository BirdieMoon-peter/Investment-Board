import type { HomepageAdviceLabelsResponse } from '../types/homepageAdvice'

export async function fetchHomepageAdviceLabels(useCache = true): Promise<HomepageAdviceLabelsResponse> {
  const response = await fetch(`/api/ai/watchlist-labels?use_cache=${useCache ? 'true' : 'false'}`)

  if (!response.ok) {
    throw new Error('Unable to load homepage AI labels right now.')
  }

  return (await response.json()) as HomepageAdviceLabelsResponse
}
