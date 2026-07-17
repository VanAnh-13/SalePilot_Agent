import assert from "node:assert/strict";
import { fileURLToPath } from "node:url";

import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";

const serverPath = fileURLToPath(new URL("./index.js", import.meta.url));
const childEnv: Record<string, string> = {};

for (const [key, value] of Object.entries(process.env)) {
  if (value !== undefined) {
    childEnv[key] = value;
  }
}

async function callSuccessfulTool(
  client: Client,
  name: string,
  args: Record<string, unknown>,
): Promise<void> {
  const result = await client.callTool({ name, arguments: args });
  assert.notEqual(result.isError, true, `${name} returned an error`);
  assert(Array.isArray(result.content) && result.content.length > 0, `${name} returned no content`);
}

async function main(): Promise<void> {
  const transport = new StdioClientTransport({
    command: process.execPath,
    args: [serverPath],
    env: childEnv,
  });
  const client = new Client(
    { name: "salepilot-mcp-smoke", version: "0.1.0" },
    { capabilities: {} },
  );

  try {
    await client.connect(transport);
    const { tools } = await client.listTools();
    const names = new Set(tools.map((tool) => tool.name));
    for (const name of [
      "salepilot_search_products",
      "salepilot_get_product",
      "salepilot_compare_products",
      "salepilot_recommend_products",
      "salepilot_search_faq",
      "salepilot_create_lead",
    ]) {
      assert(names.has(name), `Missing MCP tool: ${name}`);
    }

    await callSuccessfulTool(client, "salepilot_search_products", {
      query: "ngăn đá dưới",
      household_size: 4,
      budget_vnd: 15_000_000,
      priced_only: true,
      limit: 2,
      response_format: "json",
    });
    await callSuccessfulTool(client, "salepilot_get_product", {
      sku: "1751097000182",
      response_format: "json",
    });
    await callSuccessfulTool(client, "salepilot_compare_products", {
      skus: ["1751097000182", "1751097000181"],
      response_format: "json",
    });
    await callSuccessfulTool(client, "salepilot_recommend_products", {
      household_size: 4,
      budget_vnd: 15_000_000,
      priorities: ["tiet_kiem_dien"],
      preferred_styles: ["Ngăn đá dưới"],
      max_width_cm: 70,
      response_format: "json",
    });
    await callSuccessfulTool(client, "salepilot_search_faq", {
      query: "tồn kho",
      limit: 2,
      response_format: "json",
    });

    if (process.env.SALEPILOT_MCP_WRITE_TOKEN) {
      await callSuccessfulTool(client, "salepilot_create_lead", {
        confirmed: true,
        name: "MCP Smoke",
        phone: "0909999888",
        interest: "Tủ lạnh ngăn đá dưới cho gia đình 4 người",
        budget_vnd: 15_000_000,
        response_format: "json",
      });
    } else {
      const result = await client.callTool({
        name: "salepilot_create_lead",
        arguments: {
          confirmed: false,
          phone: "0909999888",
          interest: "Tủ lạnh cho gia đình 4 người",
          response_format: "json",
        },
      });
      assert.equal(result.isError, true);
    }
    console.log(`MCP smoke passed: ${tools.length} tool(s) available.`);
  } finally {
    await client.close();
  }
}

main().catch((error: unknown) => {
  const message = error instanceof Error ? error.message : "Unknown MCP smoke test error.";
  console.error(`MCP smoke failed: ${message}`);
  process.exitCode = 1;
});
