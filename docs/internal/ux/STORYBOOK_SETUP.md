# Storybook Setup Notes

## Version & Commands
- Storybook 9.1.10 (Vite builder)
- Scripts:
  - `npm run storybook` → dev server at http://localhost:6006
  - `npm run build-storybook` → static build (output in `storybook-static`)

## Addons installed
- `@storybook/addon-a11y`
- `@storybook/addon-docs`
- `@storybook/addon-onboarding`
- `@storybook/addon-vitest`
- `@chromatic-com/storybook`

## Vitest Integration
- Note: `@storybook/addon-vitest@9.1.10` requires `vitest ^3`, currently using `vitest ^2.1.x`. Installed using `--legacy-peer-deps`; no runtime integration yet. Evaluate upgrade to Vitest 3 or remove addon if unused.

## Theme Decorator
- Added custom theme switcher via `globalTypes` in `.storybook/preview.ts` toggling Tailwind dark class.
- Ensures component stories render in both light/dark modes for QA.

## Next Steps
1. Create foundational stories for tokens-based components (Button, Card, Input, Select).
2. Configure Chromatic (if desired) for visual regression (requires project token).
3. Add Storybook test coverage (Vitest integration, interaction testing) once Vitest version decision made.
4. Document contribution guide for new stories.
