# Plan: Frontend v2

## Components
1. Scaffold (Next 14, Tailwind, shadcn primitives, brand tokens)
2. Shell (header/nav/footer, mock auth context)
3. Landing
4. Chat (API client, messages, chips, decision, trace; `?q=` prefill)
5. Products list + detail-by-sku (list API filter)
6. Login mock
7. Build verify

## Order
Scaffold → shell → landing → api/lib → chat → products → auth → verify

## Risks
- Public backend may 502 → clear error states
- No `/products/{sku}` public route → detail finds SKU in list/search
- WIP harness: exact path allowlist only

## Verify checkpoints
After scaffold: `npm run build`
After pages: manual route check + build again
