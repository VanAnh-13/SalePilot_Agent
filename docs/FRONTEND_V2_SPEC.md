# Spec: SalePilot Frontend v2

**Status:** draft — awaiting human approval before implement  
**Date:** 2026-07-25  
**Location:** `frontend-v2/` (parallel to `frontend/`; production deploy stays on v1 until explicit switch)

## Objective

Redesign the SalePilot web experience as a **retail premium dark** consulting UI for Vietnamese shoppers and demo judges (RIVF / VAIC).

**Users**
- **Shopper (primary):** describe needs in Vietnamese → get constraint-first top-3 advice with evidence.
- **Demo viewer / researcher:** understand fail-closed, provenance, and agent path without reading the API.
- **Owner (light):** mock auth shell only — no full v1 owner dashboard in v2 scope.

**Success looks like**
- Landing sells the product story in one scroll (constraint-first, top-3, evidence, fail-closed).
- Chat feels like a premium retail assistant: chips, markdown replies, Agent Trace, Decision Evidence.
- Product browse lets users scan SKUs from the same backend catalog API.
- Auth shell is a polished mock gate (no real backend auth required in v1 API).
- Visual system is coherent (tokens, density, motion restraint) and works on mobile ≥ 360px.

## Tech Stack

| Layer | Choice | Notes |
|-------|--------|--------|
| Framework | Next.js 14 App Router | Align with v1; React 18 + TypeScript |
| Styling | Tailwind CSS 3.x | Utility-first |
| Components | shadcn/ui (Radix) | Button, Card, Input, Sheet, Dialog, Tabs, Badge, ScrollArea, Separator, Avatar, Skeleton |
| Icons | lucide-react | No emoji as primary UI icons |
| Fonts | Inter (UI) + JetBrains Mono (hashes/SKU) | via `next/font` |
| API client | Fetch helpers in `lib/api.ts` | Same contracts as `frontend/lib/api.ts` |
| Theme | CSS variables + Tailwind dark class | Dark default; optional light later out of scope |
| Port | `4000` dev | Avoid clash with v1 on `:3000`; Windows may block 3001–3100 |

**Not in stack:** heavy chart libs, i18n framework, real OAuth, state managers (use React state + localStorage).

## Commands

```bash
cd frontend-v2
npm install
npm run dev      # http://localhost:3001
npm run build    # production build must pass
npm run start    # next start -p 3001
npx tsc --noEmit # typecheck if scripted
```

Backend (unchanged): `http://localhost:8000` or `NEXT_PUBLIC_API_URL`.

## Project Structure

```
frontend-v2/
  SPEC.md                 → symlink or pointer to docs/FRONTEND_V2_SPEC.md (optional)
  package.json
  tailwind.config.ts
  postcss.config.js
  components.json         → shadcn config
  next.config.mjs
  tsconfig.json
  app/
    layout.tsx            → fonts, theme, shell
    globals.css           → Tailwind + CSS vars (brand tokens)
    page.tsx              → Landing
    chat/page.tsx         → Customer chat + trace + decision evidence
    products/page.tsx     → Catalog browse
    products/detail/page.tsx → Product detail (?sku=; list/search resolve)
    login/page.tsx        → Mock auth shell
    (optional) about not required
  components/
    layout/               → SiteHeader, SiteFooter, MobileNav
    chat/                 → MessageList, Composer, SuggestionChips, AgentTrace, DecisionPanel
    products/             → ProductCard, ProductFilters, ProductGrid
    auth/                 → LoginForm (mock)
    ui/                   → shadcn primitives
    brand/                → Logo, GradientText
  lib/
    api.ts                → API_URL + chat/products types + fetchers
    utils.ts              → cn()
    storage.ts            → external_id + message persistence keys
    format.ts             → VND, hash shortener, constraint labels (VI)
  public/                 → favicon, og optional
```

## Pages & UX

### 1. Landing `/`
- Hero: eyebrow (research/demo), H1 with gradient accent, lead copy (constraint-first điện máy), dual CTA → Chat / Products.
- “Thử ngay” quote chip that deep-links to chat with prefilled intent (query param or sessionStorage).
- Feature grid (4): ràng buộc → top-3 trade-off → bằng chứng → fail-closed.
- Trust strip: Fail-closed · Top 3 · SHA-256 provenance.
- Footer: API status hint optional; no fake metrics.

### 2. Chat `/chat`
- Full-height app shell under sticky header.
- Left/main: message stream (user bubbles right, assistant left), markdown rendering, loading skeleton.
- Composer: textarea + send; Enter to send, Shift+Enter newline.
- Suggestion chips (5 Vietnamese scenarios covering fridge/AC/washer/wearable/tablet).
- New session control (new `web-{uuid}` external_id).
- Right panel (desktop) / bottom sheet (mobile):
  - **Decision Evidence** when `decision` present (top3, constraints status, provenance hash).
  - **Agent Trace** (`trace`, `used_agents`, `run_id`, `memory_summary`).
- Error banner on API failure; offline-friendly empty states.
- Persist msgs + external_id in localStorage (same keys pattern as v1, namespaced `salepilot_v2_*` to avoid collision).

### 3. Products `/products`
- Grid of products from backend `GET /products` (pagination/query as API allows).
- Filters: text search, optional category if API returns it; price display VND.
- Card: name, price, key attrs if available, CTA “Hỏi tư vấn” → chat with product context in draft message.
- Detail route `/products/[id]` if list items expose stable id/sku; else card expands / links to chat only.
- Loading skeletons + empty + error states.
- **No fake inventory** — surface only API fields; missing stock stays unknown.

### 4. Auth shell `/login`
- Mock only: email + password UI, client-side “session” flag in localStorage (`salepilot_v2_owner`).
- Success → redirect `/` or `/products` with toast “Demo đăng nhập (mock)”.
- Header shows avatar/menu when mock-logged-in; Sign out clears flag.
- **Never** call a real auth API unless backend adds one later (ask first).
- No protected API routes in v2 — shell is visual/demo only.

### Out of scope (v2.0)
- Owner dashboard (leads, jobs, memory panels) — remains on `frontend/`.
- Real authentication / RBAC.
- Additional messaging channels (the Zalo stub was removed by owner decision).
- Replacing docker-compose `frontend` service (ask first).
- Changing backend contracts.

## Code Style

```tsx
// Preferred: small client islands, typed API, cn() for classes
"use client";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

export function SuggestionChip({
  label,
  onSelect,
  className,
}: {
  label: string;
  onSelect: (value: string) => void;
  className?: string;
}) {
  return (
    <Button
      type="button"
      variant="secondary"
      size="sm"
      className={cn("rounded-full font-normal", className)}
      onClick={() => onSelect(label)}
    >
      {label}
    </Button>
  );
}
```

**Conventions**
- Vietnamese for all customer-facing copy.
- Components: PascalCase files; hooks `useX`; lib helpers camelCase.
- No secrets; only `NEXT_PUBLIC_API_URL`.
- Prefer composition over prop-drilling mega-pages; split when page > ~200 lines.
- Accessible defaults: focus rings, `aria-label` on icon buttons, sufficient contrast on dark surfaces.

## Visual design (Retail premium dark)

| Token | Value direction |
|-------|-----------------|
| Background | Deep navy `#070b16` → `#0a1122` |
| Panel | Glass `rgba(20,28,48,0.72)` + thin border |
| Accent | Blue `#3b82f6` → teal `#22d3a5` gradient |
| Secondary accent | Violet `#8b5cf6` (trace / research) |
| Text | `#eef3ff` / muted `#8493ac` |
| Radius | 10–20px; chips full pill |
| Motion | 150–250ms ease; no parallax spam |
| Density | Chat comfortable; product grid compact |

shadcn theme mapped to these CSS variables in `globals.css`.

## API contract (reuse / mirror v1)

```ts
// POST /chat
{ message, external_id, customer_name: "Khách web", channel: "web" }
// → { reply, trace, used_agents, run_id, memory_summary, decision, ... }

// GET /products  (and detail if available)
// Use existing backend pagination/query; do not invent fields.
```

Decision / Trace types copy from `frontend/lib/api.ts` (`DecisionContract`, `TraceStep`, …).

## Testing Strategy

| Level | What | How |
|-------|------|-----|
| Build | App compiles | `cd frontend-v2 && npm run build` |
| Typecheck | TS strict | `npx tsc --noEmit` (or build) |
| Manual smoke | Landing CTAs, chat round-trip, products list, mock login | Browser against local or public API |
| Regression | v1 `frontend/` untouched | `git status` shows no unintended v1 edits |
| Contract | Chat still shows trace + decision when API returns them | Manual with known prompt |

No Playwright required for v2.0 definition-of-done (optional follow-up).

## Boundaries

**Always**
- Keep Vietnamese customer-facing strings.
- Show Agent Trace + Decision Evidence when API provides them.
- Fail closed on missing product fields (no invented stock/price).
- Run `npm run build` before marking feature passing.
- Stay inside `frontend-v2/**` + this spec + harness state files unless approved.

**Ask first**
- Point docker-compose / Vercel production at v2.
- Add real auth backend.
- Add dashboard parity pages.
- Add new npm dependencies beyond Next/Tailwind/shadcn/lucide.
- Change backend API shapes.

**Never**
- Commit `.env` or secrets.
- Edit `frontend/` v1 during this feature unless user explicitly requests a port.
- Claim real login security for the mock shell.
- Remove or skip failing build errors without fix.

## Success Criteria

1. `frontend-v2/` boots with `npm run dev` on port **3001**.
2. `npm run build` exits 0.
3. Routes exist and render: `/`, `/chat`, `/products`, `/login`.
4. Chat: send message → assistant reply; Decision panel + Trace update when present.
5. Products: list loads from API or shows clear error (no blank hang).
6. Login mock: can “sign in” and “sign out” with visible header state.
7. Mobile layout usable at 360px width (no horizontal clip on main flows).
8. `frontend/` v1 unchanged.
9. Feature recorded in `feature_list.json` with evidence after verification.

## Implementation order (preview — detailed in plan after approval)

1. Scaffold Next + Tailwind + shadcn + tokens.
2. Layout shell (header/nav/footer) + landing.
3. API client + chat page (messages, chips, trace, decision).
4. Products browse (+ detail if feasible).
5. Mock auth shell.
6. Polish responsive + build verify.

## Open Questions

1. **Product API shape:** confirm list/detail query params and fields available on target backend (local vs public). Implement against live `/products` response; degrade gracefully.
2. **Prefill from landing:** prefer `?q=` on `/chat` vs `sessionStorage`?
3. **When to switch deploy:** keep v1 on Vercel until you say switch.
4. **Harness:** `rivf-001` is currently `in_progress`. Implementing v2 requires pausing/completing it and opening a new feature (e.g. `fe-v2-001`) with whitelist `frontend-v2/**` + this spec. Confirm OK to pause `rivf-001`.

## Approval gate

Reply **approve** (and answers to open questions if any) to proceed to Phase 2 Plan → Phase 3 Tasks → Phase 4 Implement.  
Reply with edits to revise this spec first. **No application code until approval.**
