import {
  createContext,
  useContext,
  useEffect,
  useLayoutEffect,
  useMemo,
  useState,
  type CSSProperties,
  type PropsWithChildren,
} from 'react'
import { FluentProvider, webDarkTheme, webLightTheme, type Theme } from '@fluentui/react-components'

export type ThemePreference = 'system' | 'light' | 'dark'
export type ResolvedTheme = 'light' | 'dark'
export interface AppThemeValue {
  preference: ThemePreference
  resolvedTheme: ResolvedTheme
  setPreference: (value: ThemePreference) => void
}

export const THEME_PREFERENCE_STORAGE_KEY = 'investment-board-theme'

const sansFont = '"IBM Plex Sans", "PingFang SC", "Microsoft YaHei", system-ui, sans-serif'
const monoFont = '"IBM Plex Mono", "SFMono-Regular", Consolas, monospace'
const themes: Record<ResolvedTheme, Theme> = {
  light: { ...webLightTheme, fontFamilyBase: sansFont, fontFamilyNumeric: monoFont, fontFamilyMonospace: monoFont },
  dark: { ...webDarkTheme, fontFamilyBase: sansFont, fontFamilyNumeric: monoFont, fontFamilyMonospace: monoFont },
}

const ThemeContext = createContext<AppThemeValue>({
  preference: 'system',
  resolvedTheme: 'light',
  setPreference: () => {},
})

function readPreference(): ThemePreference {
  try {
    const stored = window.localStorage.getItem(THEME_PREFERENCE_STORAGE_KEY)
    return stored === 'light' || stored === 'dark' ? stored : 'system'
  } catch {
    return 'system'
  }
}

function systemTheme(): ResolvedTheme {
  return typeof window !== 'undefined' && window.matchMedia?.('(prefers-color-scheme: dark)').matches
    ? 'dark'
    : 'light'
}

// Legacy presentation and chart surfaces consume the same official palette as
// Fluent controls. The root copy also reaches drawers/menus rendered in portals.
function semanticVariables(theme: Theme): Record<string, string> {
  return {
    '--bg-app': theme.colorNeutralBackground3,
    '--bg-app-secondary': theme.colorNeutralBackground4,
    '--bg-panel': theme.colorNeutralBackground2,
    '--bg-panel-soft': theme.colorNeutralBackground3,
    '--bg-panel-strong': theme.colorNeutralBackground1,
    '--bg-hover': theme.colorNeutralBackground2Hover,
    '--border-soft': theme.colorNeutralStroke2,
    '--border-strong': theme.colorNeutralStroke1,
    '--border-input': theme.colorNeutralStrokeAccessible,
    '--text-primary': theme.colorNeutralForeground1,
    '--text-secondary': theme.colorNeutralForeground2,
    '--text-muted': theme.colorNeutralForeground3,
    '--accent': theme.colorBrandForeground1,
    '--accent-strong': theme.colorBrandForegroundLink,
    '--accent-background': theme.colorBrandBackground,
    '--accent-background-hover': theme.colorBrandBackgroundHover,
    '--accent-on': theme.colorNeutralForegroundOnBrand,
    '--accent-soft': theme.colorBrandBackground2,
    '--positive': theme.colorPaletteGreenForeground1,
    '--positive-soft': theme.colorPaletteGreenBackground1,
    '--negative': theme.colorPaletteRedForeground1,
    '--negative-soft': theme.colorPaletteRedBackground1,
    '--warning': theme.colorStatusWarningForeground1,
    '--warning-soft': theme.colorStatusWarningBackground1,
    '--font-sans': sansFont,
    '--font-mono': monoFont,
  }
}

export function useAppTheme(): AppThemeValue {
  return useContext(ThemeContext)
}

export function AppThemeProvider({ children }: PropsWithChildren) {
  const [preference, setPreference] = useState<ThemePreference>(readPreference)
  const [system, setSystem] = useState<ResolvedTheme>(systemTheme)
  const resolvedTheme = preference === 'system' ? system : preference
  const theme = themes[resolvedTheme]
  const variables = useMemo(() => semanticVariables(theme), [theme])
  const value = useMemo(() => ({ preference, resolvedTheme, setPreference }), [preference, resolvedTheme])

  useEffect(() => {
    const media = window.matchMedia?.('(prefers-color-scheme: dark)')
    if (!media) return
    const onChange = () => setSystem(media.matches ? 'dark' : 'light')
    onChange()
    media.addEventListener('change', onChange)
    return () => media.removeEventListener('change', onChange)
  }, [])

  useEffect(() => {
    try {
      window.localStorage.setItem(THEME_PREFERENCE_STORAGE_KEY, preference)
    } catch {
      // Storage restrictions must not prevent a session-only appearance choice.
    }
  }, [preference])

  useLayoutEffect(() => {
    const root = document.documentElement
    const previousTheme = root.getAttribute('data-theme')
    const previousScheme = root.style.colorScheme
    const previousVariables = Object.keys(variables).map((key) => [key, root.style.getPropertyValue(key)])
    root.dataset.theme = resolvedTheme
    root.style.colorScheme = resolvedTheme
    Object.entries(variables).forEach(([key, color]) => root.style.setProperty(key, color))
    return () => {
      if (previousTheme === null) root.removeAttribute('data-theme')
      else root.setAttribute('data-theme', previousTheme)
      root.style.colorScheme = previousScheme
      previousVariables.forEach(([key, color]) => {
        if (color) root.style.setProperty(key, color)
        else root.style.removeProperty(key)
      })
    }
  }, [resolvedTheme, variables])

  return (
    <ThemeContext.Provider value={value}>
      <FluentProvider theme={theme} className="app-theme-provider" style={variables as CSSProperties}>
        {children}
      </FluentProvider>
    </ThemeContext.Provider>
  )
}
