import rawTokens from './tokens.json'

export type ColorScale = Record<string, string>

export interface SemanticColor {
  DEFAULT: string
  surface: string
}

export interface DesignTokens {
  colors: {
    brand: {
      green: string
      greenLight: string
      greenDark: string
      silver: string
      dark: string
      darker: string
    }
    primary: ColorScale
    neutral: ColorScale
    semantic: {
      success: SemanticColor
      danger: SemanticColor
      warning: SemanticColor
      info: SemanticColor
    }
  }
  typography: {
    family: {
      sans: string
      mono: string
    }
    sizes: Record<string, string>
    lineHeights: Record<string, string>
  }
  spacing: Record<string, string>
  radii: Record<string, string>
  shadows: Record<string, string>
  transitions: {
    fast: string
    medium: string
    slow: string
    easing: string
  }
}

export const tokens = rawTokens as DesignTokens

export type TokenCategory = keyof DesignTokens

export function getColorScale<K extends keyof DesignTokens['colors']>(name: K): DesignTokens['colors'][K] {
  return tokens.colors[name]
}

export const designTokens = tokens

export default tokens
