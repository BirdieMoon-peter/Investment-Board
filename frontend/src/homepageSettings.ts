import type { Language } from './i18n'

export type HomepageMode = 'live' | 'focused'
export type HomepageDensity = 'comfortable' | 'compact'

export interface HomepageSettings {
  homepageMode: HomepageMode
  density: HomepageDensity
  showHero: boolean
  showSpotlight: boolean
  showMarketIndexes: boolean
  showMacroPanel: boolean
  showAiTags: boolean
  autoRefreshEnabled: boolean
  autoRefreshIntervalMs: number
  autoSyncEnabled: boolean
  autoSyncIntervalMs: number
  language: Language
}

export const DEFAULT_HOMEPAGE_SETTINGS: HomepageSettings = {
  homepageMode: 'live',
  density: 'compact',
  showHero: true,
  showSpotlight: true,
  showMarketIndexes: true,
  showMacroPanel: true,
  showAiTags: true,
  autoRefreshEnabled: true,
  autoRefreshIntervalMs: 60_000,
  autoSyncEnabled: true,
  autoSyncIntervalMs: 180_000,
  language: 'en',
}

export const HOMEPAGE_SETTINGS_STORAGE_KEY =
  'investment-board-homepage-settings'

const validRefreshIntervals = new Set([60_000, 120_000, 300_000])
const validSyncIntervals = new Set([180_000, 300_000, 600_000])

export function loadHomepageSettings(): HomepageSettings {
  if (typeof window === 'undefined') {
    return DEFAULT_HOMEPAGE_SETTINGS
  }

  try {
    const rawValue = window.localStorage.getItem(HOMEPAGE_SETTINGS_STORAGE_KEY)
    if (!rawValue) return DEFAULT_HOMEPAGE_SETTINGS
    const parsed = JSON.parse(rawValue) as Partial<HomepageSettings>
    return {
      homepageMode: parsed.homepageMode === 'focused' ? 'focused' : 'live',
      density:
        parsed.density === 'comfortable'
          ? 'comfortable'
          : DEFAULT_HOMEPAGE_SETTINGS.density,
      showHero:
        typeof parsed.showHero === 'boolean'
          ? parsed.showHero
          : DEFAULT_HOMEPAGE_SETTINGS.showHero,
      showSpotlight:
        typeof parsed.showSpotlight === 'boolean'
          ? parsed.showSpotlight
          : DEFAULT_HOMEPAGE_SETTINGS.showSpotlight,
      showMarketIndexes:
        typeof parsed.showMarketIndexes === 'boolean'
          ? parsed.showMarketIndexes
          : DEFAULT_HOMEPAGE_SETTINGS.showMarketIndexes,
      showMacroPanel:
        typeof parsed.showMacroPanel === 'boolean'
          ? parsed.showMacroPanel
          : DEFAULT_HOMEPAGE_SETTINGS.showMacroPanel,
      showAiTags:
        typeof parsed.showAiTags === 'boolean'
          ? parsed.showAiTags
          : DEFAULT_HOMEPAGE_SETTINGS.showAiTags,
      autoRefreshEnabled:
        typeof parsed.autoRefreshEnabled === 'boolean'
          ? parsed.autoRefreshEnabled
          : DEFAULT_HOMEPAGE_SETTINGS.autoRefreshEnabled,
      autoRefreshIntervalMs: validRefreshIntervals.has(
        parsed.autoRefreshIntervalMs ?? 0,
      )
        ? (parsed.autoRefreshIntervalMs as number)
        : DEFAULT_HOMEPAGE_SETTINGS.autoRefreshIntervalMs,
      autoSyncEnabled:
        typeof parsed.autoSyncEnabled === 'boolean'
          ? parsed.autoSyncEnabled
          : DEFAULT_HOMEPAGE_SETTINGS.autoSyncEnabled,
      autoSyncIntervalMs: validSyncIntervals.has(parsed.autoSyncIntervalMs ?? 0)
        ? (parsed.autoSyncIntervalMs as number)
        : DEFAULT_HOMEPAGE_SETTINGS.autoSyncIntervalMs,
      language: parsed.language === 'zh' ? 'zh' : 'en',
    }
  } catch {
    return DEFAULT_HOMEPAGE_SETTINGS
  }
}

export function saveHomepageSettings(settings: HomepageSettings) {
  if (typeof window === 'undefined') {
    return
  }

  try {
    window.localStorage.setItem(
      HOMEPAGE_SETTINGS_STORAGE_KEY,
      JSON.stringify(settings),
    )
  } catch {
    // Browser policy or quota must not prevent session-only preference changes.
  }
}
