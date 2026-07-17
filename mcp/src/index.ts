import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";

import { SalePilotApiClient } from "./api-client.js";
import { registerSalePilotTools } from "./tools.js";

async function main(): Promise<void> {
  const server = new McpServer({
    name: "salepilot-mcp-server",
    version: "0.1.0",
  });
  registerSalePilotTools(server, new SalePilotApiClient());
  await server.connect(new StdioServerTransport());
}

main().catch((error: unknown) => {
  const message = error instanceof Error ? error.message : "Unknown MCP server startup error.";
  console.error(`SalePilot MCP failed to start: ${message}`);
  process.exitCode = 1;
});
