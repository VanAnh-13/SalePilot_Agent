# Frontend context (SalePilot)

Loaded by coding agents when working under `frontend/`.

## Stack

- Next.js 14 App Router + React 18 + TypeScript
- Plain CSS (`app/globals.css`) — no Tailwind required
- API base: `NEXT_PUBLIC_API_URL` (default backend `http://localhost:8000`)

## Commands

```bash
cd frontend
npm install
npm run dev    # :3000
npm run build  # production
```

Backend must be up on `:8000` for chat/dashboard.

## Layout

| Path | Role |
|------|------|
| `app/page.tsx` | Landing |
| `app/chat/page.tsx` | Customer chat + Agent Trace |
| `app/dashboard/page.tsx` | Leads, conversations, Zalo outbox |
| `lib/api.ts` | Fetch helpers |
| `components/Nav.tsx` | Nav |

## Rules

- Keep Vietnamese UI copy for customer-facing strings.
- Agent Trace must show `trace` / `used_agents` from `/chat` response.
- Do not hardcode secrets; only `NEXT_PUBLIC_API_URL`.
- Prefer small components; no heavy UI framework unless requested.
