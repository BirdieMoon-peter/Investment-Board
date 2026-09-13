import type { HomepageOverview } from '../types/homepage'

export async function fetchHomepageOverview(): Promise<HomepageOverview> {
  const response = await fetch('/api/homepage/overview')

  if (!response.ok) {
    throw new Error('Unable to load homepage overview right now.')
  }

  return (await response.json()) as HomepageOverview
}
