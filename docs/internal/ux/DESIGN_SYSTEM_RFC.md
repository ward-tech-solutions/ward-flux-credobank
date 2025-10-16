# RFC: Ward OPS Design System 2.0

**Status**: Draft  
**Owner**: UI/UX Workstream  
**Reviewers**: Frontend, Product, Brand  
**Target Decision Date**: 2025-02-15

## 1. Why
- Current UI mixes legacy (2019) and modern (2025) styles → inconsistent visuals and UX.
- Repeated styling decisions live inline in components (duplicate shadows, spacing, colors).
- Dark-mode bugs surface because tokens are not centralised.
- Designers/devs lack a single source of truth (no Storybook, no token inventory).

## 2. Goals
1. Establish a reusable design language (tokens → components → patterns).
2. Guarantee accessibility (WCAG AA) for light/dark themes by construction.
3. Accelerate development via documented component API & examples.
4. Align brand identity with modern product expectations (glassmorphism, subtle motion).
5. Make future theming (regional editions, white-label) straightforward.

## 3. Requirements
- **Token Layer**
  - Color palette (semantic + brand) defined in one place (Tailwind config + JSON export).
  - Typography scale (font family, weights, sizes) with responsive ramp.
  - Spacing scale (4px increment baseline) codified.
  - Radii, shadows, borders, blur values referenced by name.
  - Motion tokens (durations, easing, transform defaults).
- **Component Layer**
  - Documented primitives (`Button`, `Card`, `Input`, `Select`, `Table`, `Modal`, `Badge`, `Tabs`, `Skeleton`, `Avatar`, `Tooltip`).
  - Variants (primary/secondary, glass/solid, success/danger) mapped to tokens.
  - Accessibility notes per component (keyboard focus, ARIA roles).
  - Storybook (or Ladle) sandbox with interactive controls.
- **Pattern Layer**
  - Layout templates (Dashboard grid, Metrics + Table, Wizard, Modal form).
  - Feedback surfaces (toasts, inline banners, loading skeletons, progress).
  - Navigation (sidebar, header, breadcrumbs, command palette).
  - Data visualisation styling governance (colors, gridlines, empty states).
- **Governance**
  - Contribution guide for adding/updating components.
  - Visual regression testing (Chromatic/Storybook or Playwright screenshot diff).
  - Release notes for design system changes.

## 4. Current State Audit (2025-??-??)
- **Tokens**
  - Tailwind `extend.colors` defines brand + semantic palette, but light/dark specifics and neutral scale missing.
  - Shadows (`shadow-ward`, `shadow-ward-lg`) and radii declared; need consistent use.
  - No formal spacing or motion tokens.
- **Components**
  - UI primitives exist (`Button`, `Card`, `Select`, `MultiSelect`, `Modal`, `Table`) but variant props undocumented.
  - Some pages still use bespoke markup (Discovery tables, Diagnostics forms).
- **Patterns**
  - Dashboard/Monitor updated; Discovery/Diagnostics/Reports not.
  - Dark mode inconsistent (Alert Rules filters, map overlays).
  - No command palette or onboarding surfaces yet.

## 5. Proposal
1. **Token Registry**
   - Create `frontend/src/design/tokens.ts` exporting color/spacing/typography/motion tokens.
   - Sync tokens with Tailwind config via generated file and Figma (using Style Dictionary).
2. **Component Catalog**
   - Build Storybook with `@storybook/react` (or use Ladle for quick start).
   - Migrate existing components into `frontend/src/components/ui` with prop tables.
   - Add docs stories for each variant, including dark mode.
3. **Design Ops**
   - Maintain `docs/ux/PATTERNS.md` summarising layout recipes.
   - Introduce lint rule set (stylelint/tailwindcss-classnames) to enforce token usage.
   - Add Chromatic (or Storybook test runner) to CI for visual regression.
4. **Rollout Plan**
   - Sprint 1: tokens + Storybook skeleton + migrate Button/Card/Input.
   - Sprint 2: rest of primitives + layout templates.
   - Sprint 3: adopt new components across Dashboard, Devices, Monitor.
   - Sprint 4: align legacy pages; retire deprecated CSS.
5. **Success Criteria**
   - 100% UI components showcased in Storybook.
   - Automated accessibility check passes (axe) in CI for components.
   - Visual regression suite integrated with PR workflow.
   - Designers have mapped tokens to Figma library.

## 6. Open Questions
- Do we adopt Tailwind CSS Variables for theming or rely on Tailwind config only?
- Preferred Storybook hosting (Chromatic vs. self-hosted vs. GitHub Pages)?
- Should charts migrate to a standard theming wrapper (e.g., Recharts theme provider)?
- How do we version the design system (semver + NPM package, or monorepo exports)?

## 7. Next Steps
1. Approve scope/goals with product & brand stakeholders.
2. Create GitHub Epic + issues for token registry, Storybook setup, component migration.
3. Draft tokens JSON and align with existing Tailwind config (see `frontend/tailwind.config.js`).
4. Produce initial Storybook stories for `Button`, `Card`, `Input`, `Select`, `Modal`.
5. Schedule design review once first set of components rendered in Storybook.

---

*Document owner to update status and decisions as the RFC progresses.*
