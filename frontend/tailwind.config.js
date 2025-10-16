import { readFileSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const tokensPath = path.resolve(__dirname, './src/design/tokens.json')
const tokens = JSON.parse(readFileSync(tokensPath, 'utf-8'))

const { colors, typography, spacing, radii, shadows, transitions } = tokens

const parseFontStack = (stack) =>
  stack
    .split(',')
    .map((item) => item.trim().replace(/^'(.*)'$/, '$1').replace(/^"(.*)"$/, '$1'))

const fontSans = parseFontStack(typography.family.sans)
const fontMono = parseFontStack(typography.family.mono)

/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ['class'],
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        // WARD Brand Colors (preserve original identity!)
        ward: {
          green: colors.brand.green,
          'green-light': colors.brand.greenLight,
          'green-dark': colors.brand.greenDark,
          silver: colors.brand.silver,
          dark: colors.brand.dark,
          darker: colors.brand.darker,
        },
        // Modern semantic colors
        primary: {
          DEFAULT: colors.primary['500'],
          ...colors.primary,
        },
        neutral: {
          ...colors.neutral,
        },
        success: colors.semantic.success.DEFAULT,
        danger: colors.semantic.danger.DEFAULT,
        warning: colors.semantic.warning.DEFAULT,
        info: colors.semantic.info.DEFAULT,
        'success-surface': colors.semantic.success.surface,
        'danger-surface': colors.semantic.danger.surface,
        'warning-surface': colors.semantic.warning.surface,
        'info-surface': colors.semantic.info.surface,
      },
      fontFamily: {
        sans: fontSans,
        mono: fontMono,
      },
      borderRadius: {
        ...radii,
      },
      boxShadow: {
        ...shadows,
        'ward': shadows.ward,
        'ward-lg': shadows.wardLg,
      },
      spacing: {
        ...spacing,
      },
      transitionDuration: {
        fast: transitions.fast,
        DEFAULT: transitions.medium,
        slow: transitions.slow,
      },
      transitionTimingFunction: {
        brand: transitions.easing,
      },
    },
  },
  plugins: [],
}
