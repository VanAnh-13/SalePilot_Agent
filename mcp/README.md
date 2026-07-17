# SalePilot MCP Server

Local stdio MCP server for the SalePilot refrigerator advisor. It exposes the provided Google Sheet's `Tủ Lạnh` tab (`category_code=38`), comparison, need-based top-3 recommendations, guidance FAQ, and a consent-gated CRM lead write.

```text
MCP client --stdio--> Node.js MCP server --HTTP--> SalePilot FastAPI /mcp endpoints
```

The MCP server does not duplicate catalog ranking or CRM persistence. Those rules remain in the FastAPI backend.

## Requirements

- Node.js 20+
- SalePilot backend running locally on `http://127.0.0.1:8000`

Install and build:

```bash
cd mcp
npm ci
npm run build
```

## Client configuration

Use the compiled entry point with a local MCP client:

```json
{
  "mcpServers": {
    "salepilot": {
      "command": "node",
      "args": ["/absolute/path/to/hackathon_base/mcp/dist/index.js"],
      "env": {
        "SALEPILOT_API_BASE_URL": "http://127.0.0.1:8000"
      }
    }
  }
}
```

The bridge rejects non-local API hosts by default. Set `SALEPILOT_ALLOW_REMOTE_API=true` only when the configured remote endpoint is trusted.

## Tools

| Tool | Behavior |
| --- | --- |
| `salepilot_search_products` | Paginated search by keyword, price, household size, capacity, dimensions, brand, or style |
| `salepilot_get_product` | Full catalog detail for one SKU |
| `salepilot_compare_products` | Compare 2-5 SKUs by current price, capacity, width, and discount |
| `salepilot_recommend_products` | Deterministic diversified top-3 recommendation or clarification questions |
| `salepilot_search_faq` | Paginated policy FAQ search |
| `salepilot_create_lead` | Creates a CRM lead after explicit customer confirmation |

Read tools support `response_format: "markdown" | "json"` and always provide structured MCP content.

The snapshot contains 1,692 refrigerator SKUs; 252 have a current source price and are eligible for recommendation. Rows without price remain searchable for specification lookup. The sheet has no stock column, so no tool claims availability.

## Lead write security

Lead creation is disabled by default. It requires all of the following:

1. Set a secret `MCP_WRITE_TOKEN` in the backend environment.
2. Pass the same value as `SALEPILOT_MCP_WRITE_TOKEN` to the MCP server process.
3. Call `salepilot_create_lead` with `confirmed: true` only after the customer explicitly agrees to share their contact information.

```bash
# Backend environment
MCP_WRITE_TOKEN=replace-with-a-long-random-secret

# MCP client/server environment
SALEPILOT_MCP_WRITE_TOKEN=replace-with-a-long-random-secret
```

The API returns `503` while lead writes are disabled and `401` for a missing or invalid token. The server never writes logs to stdout because stdout is reserved for MCP JSON-RPC.

## Backend contract

The Node server calls these backend endpoints:

| Endpoint | Purpose |
| --- | --- |
| `GET /mcp/products` | Filtered, paginated catalog list |
| `GET /mcp/products/{sku}` | Single catalog product |
| `POST /mcp/product-comparisons` | Compare selected SKUs |
| `POST /mcp/recommendations` | Top-3 recommendation |
| `GET /mcp/knowledge/faq` | Paginated FAQ search |
| `POST /mcp/leads` | Token-protected, consent-gated lead creation |

## Verification

With the backend running:

```bash
./scripts/verify.sh
cd mcp
npm run build
SALEPILOT_API_BASE_URL=http://127.0.0.1:8000 npm run smoke
```

`npm run smoke` uses the official MCP SDK client over stdio. It verifies tool discovery and every read-only tool; it also verifies the no-consent lead path. When `SALEPILOT_MCP_WRITE_TOKEN` is configured against a backend with the matching `MCP_WRITE_TOKEN`, it verifies a real lead write.

To inspect tools interactively:

```bash
npx @modelcontextprotocol/inspector \
  -e SALEPILOT_API_BASE_URL=http://127.0.0.1:8000 \
  node dist/index.js
```

## Evaluations

`evaluations.xml` contains ten independent, read-only evaluation questions with stable answers derived from the checked-in category-code-38 snapshot and FAQ data.
