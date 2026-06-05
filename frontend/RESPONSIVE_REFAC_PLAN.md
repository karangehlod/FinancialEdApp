# Responsive & Sizing Refactor Plan — FinancialEd Frontend

Goal
- Make the UI visually consistent and usable across all screen sizes: elements (logo, icons, typography, spacing) must scale fluidly and proportionally when viewport size changes.
- Replace ad-hoc fixed sizes with a small set of fluid tokens (clamp-based) and derive all component sizes from them so changes are predictable and maintainable.
- Audit and refactor components to use these tokens and enforce usage via patterns and tests.

Scope
- Files: all files under `frontend/src/` (high priority subset listed below). Changes span `index.css`, core layout components, and high-impact pages (Login, Register, Chat, Dashboard).
- Deliverables: staged PRs (Plan + Phase1 PR + refactor PRs), automated snapshot/visual tests, and documentation of responsive tokens and usage.

High-level approach and principles
- Single source of truth: centralize fluid tokens in `index.css` and derive all sizes from them. Primary token: `--header-height` (fluid via clamp()).
- Fluid-first: use clamp() and viewport-aware formulas so values grow/shrink smoothly instead of stepping only at breakpoints.
- Derive everything: icons, logo, badges, button heights, spacing, and typography derive from header height or a small set of base tokens using fixed ratios.
- Container-aware: use container queries where component sizing should depend on component width rather than global viewport.
- Progressive rollout: implement global token changes first, then component-level updates to minimize regressions.
- Enforceable patterns: provide an `Icon` wrapper and `token` CSS classes so developers use tokens rather than pixels.

Fluid scaling strategy (core)
- Make `--header-height` fluid with clamp(): e.g. --header-height: clamp(40px, calc(3.5vw + 20px), 80px);
  - This produces a smoothly scaling header from small phones to large desktops.
- Derive other tokens relative to `--header-height`:
  - --sidebar-logo-size: calc(var(--header-height) * 0.9)
  - --icon-md: calc(var(--header-height) * 0.28)
  - --icon-sm: calc(var(--icon-md) * 0.75)
  - --page-icon-size: clamp(40px, calc(var(--header-height) * 1.2), 180px)
  - Typography: tie base font-size to clamp() (e.g., --font-base: clamp(0.9rem, 1.6vw, 1rem)) and derive larger scales from it.
- Use ratios everywhere so components retain proportion when header changes.

Prioritized tasks (phased)

Phase 0 — Plan & safety (done)
- Created this plan file and will add a responsive checklist for reviewers.

Phase 1 — Fluid tokens & quick wins (high impact, low risk)
- Update `frontend/src/index.css` with fluid tokens:
  - Implement `--header-height` as a clamp() expression.
  - Create derived tokens for icons, logo, typography, spacing, and buttons using fixed ratios from `--header-height` or `--font-base`.
  - Add utility classes: `.icon-sm`, `.icon-md`, `.icon-lg`, `.text-xs-fluid`, `.text-sm-fluid`, etc., that map to tokens.
  - Add container-query fallbacks for components that need to scale by container width.
- Update `frontend/src/components/Layout.jsx`:
  - Make header padding responsive to token (e.g., `padding: calc(var(--header-height) * 0.12) 1rem;`).
  - Replace many `size={...}` icon props with wrapper classes using `.icon-md` etc.
- Quick component tweaks:
  - `ChatComponent.jsx`: replace fixed heights with min-height using clamp()/viewport-based logic.
  - `UI.jsx`: expose an `IconWrapper` helper or CSS classes and ensure button/input heights derive from tokens.

Deliverable: PR 1 with token changes + Layout + a couple of component fixes (small, reversible).

Phase 2 — Component audit & proportional refactor (medium effort)
- Programmatic audit: search for fixed px values for paddings, font sizes, heights, and icon numeric props.
- Replace patterns with fluid tokens or responsive Tailwind variants:
  - Replace `px-4 py-3`, `text-2xl` on key hero and header components with token-driven styles or responsive classes `text-base sm:text-lg` tied to `--font-base`.
  - Convert hard `size={20}` icon props to CSS-based sizing where possible.
  - Use container queries for components inside constrained panels (tables, cards).
- Create small helper components to enforce patterns:
  - `<FluidIcon size="md" />` wrapper that reads CSS tokens and renders SVGs with correct width/height.
  - Export small `tokens.js` (or CSS reference) documenting ratios for developers.

Phase 3 — Testing, visual regression, and QA
- Add visual snapshot tests for Layout (header+sidebar) and a few pages at multiple widths (360, 428, 768, 1024, 1366).
- Manual QA checklist across breakpoints to verify proportional scaling and no overflows.
- Add container-query based tests for components that scale by container.

Phase 4 — CI & docs
- Add `RESPONSIVE_CHECKLIST.md` and `RESPONSIVE_TOKENS.md` documenting tokens, ratios, and usage examples.
- Add CI step that runs snapshot tests and fails on large regressions.

Concrete per-file actions (first-pass)
- `frontend/src/index.css`
  - Implement fluid `--header-height` and derived tokens. Add utility classes for icons and fluid text.
- `frontend/src/components/Layout.jsx`
  - Use token-driven padding and icon wrappers.
- `frontend/src/components/UI.jsx`
  - Provide `IconWrapper` and ensure inputs/buttons reference token-driven heights.
- `frontend/src/components/ChatComponent.jsx`
  - Replace fixed heights with clamp/min-height.
- `frontend/src/pages/LoginPage.jsx`, `RegisterPage.jsx`
  - Ensure hero/logo uses `--page-hero-icon-size` and that typography uses `--font-base` with scaled variants.

Testing plan
- Unit tests: ensure components render and snapshots match expected proportional layout.
- Visual tests: snapshots at multiple widths (mobile to large desktop).
- Manual QA: confirm computed token values in browser devtools and inspect for overflow.

Risk mitigation & rollback
- Phase 1 will be a small PR to validate tokens and critical layout changes. Revertible and low risk.
- Keep changes isolated and provide screenshots for review.

PR strategy
- PR 1 (Phase 1): token + Layout + small fixes.
- PR 2 (Phase 2): component refactor in small grouped PRs.
- PR 3 (Phase 3): tests + docs.

Metrics for acceptance
- Elements scale smoothly across viewport sizes (no abrupt jumps). On small phones (360px) logo/text/icons should feel proportional and not oversized.
- No horizontal scroll or overflow.
- Snapshot tests for header and sidebar pass at mobile/tablet/desktop widths.

Next step
- I will implement Phase 1 (token changes + quick fixes). Confirm `Proceed with Phase 1` to start implementing changes.
