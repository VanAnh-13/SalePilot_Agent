# Quality Document — SalePilot

**Update cadence:** After each significant session, or before VAIC demo day.

**Grading scale:** A (solid) · B (ok, minor gaps) · C (partial) · D (broken)

---

## Product Domains

| Domain | Grade | Verification | Agent Legibility | Test Stability | Key Gaps | Last Updated |
|--------|-------|-------------|-----------------|---------------|----------|-------------|
| Multi-agent chat | B | Manual + offline smoke | High | Low (few automated tests) | Need pytest/API suite | 2026-07-17 |
| Catalog / pricing tools | B | Offline smoke | High | Low | Search ranking rough offline | 2026-07-17 |
| Knowledge / FAQ | B | Offline smoke | High | Low | RAG is lexical + optional Chroma | 2026-07-17 |
| CRM / leads | B | Seed + create_lead offline | High | Low | No auth multi-tenant | 2026-07-17 |
| Zalo channel stub | B | Module present | High | Low | Need recorded simulate evidence | 2026-07-17 |
| Owner dashboard UI | C | Code only | Medium | None | No browser evidence | 2026-07-17 |
| Deploy / live URL | D | — | — | — | Not deployed | 2026-07-17 |

## Architectural Layers

| Layer | Grade | Boundary Enforcement | Agent Legibility | Key Gaps | Last Updated |
|-------|-------|---------------------|-----------------|----------|-------------|
| Agent graph (Lead/sub) | B | Sub-agent tool whitelist | High | LLM vs offline dual path | 2026-07-17 |
| Tools / DB | B | SQLAlchemy models | High | SQLite only by default | 2026-07-17 |
| Channels | B | Zalo adapter protocol | High | Mock-only client default | 2026-07-17 |
| API (FastAPI) | B | Routers by domain | High | Little validation on edge cases | 2026-07-17 |
| Frontend (Next.js) | C | Simple pages | Medium | No shared design system | 2026-07-17 |
| Harness artifacts | A | AGENTS + feature_list | High | Keep evidence honest | 2026-07-17 |

## Change History

### 2026-07-17

- Changes: initial scaffold + harness pack
- Domains promoted: multi-agent chat to B
- Demoted: —
- New gaps: automated tests, deploy
- Gaps closed: empty repo
