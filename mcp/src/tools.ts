import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";

import {
  ComparisonSchema,
  FaqPageSchema,
  LeadCreatedSchema,
  ProductPageSchema,
  ProductSchemaOutput,
  RecommendationSchema,
  SalePilotApiClient,
  SalePilotApiError,
} from "./api-client.js";

const ResponseFormatSchema = z.enum(["markdown", "json"]).default("markdown");
type ResponseFormat = z.infer<typeof ResponseFormatSchema>;

function field(record: object, key: string): string {
  const value = Reflect.get(record, key);
  return typeof value === "string" || typeof value === "number" ? String(value) : "-";
}

function records(value: unknown): Record<string, unknown>[] {
  return Array.isArray(value)
    ? value.filter(
        (item): item is Record<string, unknown> => item !== null && typeof item === "object",
      )
    : [];
}

function strings(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : [];
}

function formatProducts(page: z.infer<typeof ProductPageSchema>): string {
  if (page.items.length === 0) {
    return "Không tìm thấy tủ lạnh phù hợp trong snapshot category_code=38.";
  }
  const products = page.items.map((product) => {
    return `- **${field(product, "sku")}**: ${field(product, "name")} | ${field(product, "price_display")} | ${field(product, "usable_capacity_l")} lít | ${field(product, "household_size_label")}`;
  });
  return [`## Tủ lạnh (${page.total_count})`, ...products].join("\n");
}

function formatProduct(product: Record<string, unknown>): string {
  const details = [
    `- SKU: **${field(product, "sku")}**`,
    `- Tên hiển thị: ${field(product, "name")}`,
    `- Giá hiện tại: ${field(product, "price_display")}`,
    `- Kiểu tủ: ${field(product, "style")}`,
    `- Dung tích sử dụng: ${field(product, "usable_capacity_l")} lít`,
    `- Số người theo bảng: ${field(product, "household_size_label")}`,
    `- Ngang × cao × sâu: ${field(product, "width_cm")} × ${field(product, "height_cm")} × ${field(product, "depth_cm")} cm`,
    `- Tiết kiệm điện: ${field(product, "energy_saving_technology")}`,
    `- Công nghệ bảo quản: ${field(product, "food_preservation_technology")}`,
    `- Tồn kho: không có trong bảng nguồn`,
    `- Nguồn: ${field(product, "source")}`,
  ];
  return [`## ${field(product, "name")}`, ...details].join("\n");
}

function formatComparison(comparison: Record<string, unknown>): string {
  const items = records(comparison.items).map((product) => {
    return `- ${field(product, "sku")}: ${field(product, "name")} (${field(product, "price_display")}, ${field(product, "usable_capacity_l")} lít)`;
  });
  const tradeoffs = strings(comparison.tradeoffs).map((tradeoff) => `- ${tradeoff}`);
  return ["## So sánh tủ lạnh", ...items, "", "### Trade-off", ...tradeoffs].join("\n");
}

function formatRecommendation(recommendation: Record<string, unknown>): string {
  if (recommendation.need_more === true) {
    return [
      "## Cần thêm thông tin",
      ...strings(recommendation.ask).map((question) => `- ${question}`),
    ].join("\n");
  }
  if (recommendation.ok === false) {
    return `## Không tìm thấy mẫu phù hợp\n${field(recommendation, "message")}`;
  }
  const products = records(recommendation.top3).map((product, index) => {
    return `${index + 1}. **${field(product, "sku")}** - ${field(product, "name")} (${field(product, "price_display")})\n   ${field(product, "why")}`;
  });
  const tradeoffs = strings(recommendation.tradeoffs).map((tradeoff) => `- ${tradeoff}`);
  const disclaimer = field(recommendation, "disclaimer");
  return [
    "## Top 3 tủ lạnh",
    ...products,
    "",
    "### Trade-off",
    ...tradeoffs,
    "",
    disclaimer,
  ].join("\n");
}

function formatFaq(page: z.infer<typeof FaqPageSchema>): string {
  if (page.items.length === 0) {
    return "Không tìm thấy nội dung phù hợp trong knowledge base.";
  }
  return [
    `## Hướng dẫn và chính sách (${page.total_count})`,
    ...page.items.map((faq) => `### ${faq.question}\n${faq.answer}`),
  ].join("\n\n");
}

function toolResult<T extends Record<string, unknown>>(
  data: T,
  responseFormat: ResponseFormat,
  markdown: string,
) {
  return {
    content: [
      {
        type: "text" as const,
        text: responseFormat === "json" ? JSON.stringify(data, null, 2) : markdown,
      },
    ],
    structuredContent: data,
  };
}

function toolError(error: unknown) {
  const message =
    error instanceof SalePilotApiError
      ? error.message
      : "SalePilot MCP could not complete the request. Check the server configuration and retry.";
  return {
    content: [{ type: "text" as const, text: message }],
    isError: true,
  };
}

export function registerSalePilotTools(server: McpServer, api: SalePilotApiClient): void {
  server.registerTool(
    "salepilot_search_products",
    {
      title: "Search SalePilot Refrigerators",
      description:
        "Search all refrigerator rows from Google Sheet category_code=38 by keyword, current price, household size, capacity, dimensions, energy-saving technology, brand, or style. Rows without price remain searchable; set priced_only=true for currently priced products.",
      inputSchema: z.object({
        query: z.string().max(200).optional().describe("Keyword, SKU, model code, feature, or technology"),
        budget_vnd: z.number().int().nonnegative().max(1_000_000_000).optional(),
        household_size: z.number().int().min(1).max(20).optional(),
        min_capacity_l: z.number().int().min(1).max(2_000).optional(),
        max_width_cm: z.number().positive().max(500).optional(),
        max_height_cm: z.number().positive().max(500).optional(),
        max_depth_cm: z.number().positive().max(500).optional(),
        energy_saving: z.boolean().optional(),
        brand: z.string().max(80).optional(),
        style: z.string().max(100).optional(),
        priced_only: z.boolean().default(false),
        limit: z.number().int().min(1).max(50).default(20),
        offset: z.number().int().nonnegative().default(0),
        response_format: ResponseFormatSchema,
      }),
      outputSchema: ProductPageSchema,
      annotations: {
        readOnlyHint: true,
        destructiveHint: false,
        idempotentHint: true,
        openWorldHint: false,
      },
    },
    async ({ response_format, ...params }) => {
      try {
        const page = await api.searchProducts(params);
        return toolResult(page, response_format, formatProducts(page));
      } catch (error) {
        return toolError(error);
      }
    },
  );

  server.registerTool(
    "salepilot_get_product",
    {
      title: "Get a SalePilot Refrigerator",
      description:
        "Get one refrigerator SKU with source-backed capacity, dimensions, technologies, current/original prices, promotions, and original spreadsheet specifications. This tool never claims stock availability.",
      inputSchema: z.object({
        sku: z.string().trim().min(3).max(32).describe("Numeric source SKU, for example 1751097000182"),
        response_format: ResponseFormatSchema,
      }),
      outputSchema: ProductSchemaOutput,
      annotations: {
        readOnlyHint: true,
        destructiveHint: false,
        idempotentHint: true,
        openWorldHint: false,
      },
    },
    async ({ sku, response_format }) => {
      try {
        const product = await api.getProduct(sku);
        return toolResult(product, response_format, formatProduct(product));
      } catch (error) {
        return toolError(error);
      }
    },
  );

  server.registerTool(
    "salepilot_compare_products",
    {
      title: "Compare SalePilot Refrigerators",
      description:
        "Compare two to five refrigerator SKUs by current price, usable capacity, width, and discount using category_code=38 source facts.",
      inputSchema: z.object({
        skus: z
          .array(z.string().trim().min(3).max(32))
          .min(2)
          .max(5)
          .refine((skus) => new Set(skus).size === skus.length, { message: "SKUs must be unique." }),
        response_format: ResponseFormatSchema,
      }),
      outputSchema: ComparisonSchema,
      annotations: {
        readOnlyHint: true,
        destructiveHint: false,
        idempotentHint: true,
        openWorldHint: false,
      },
    },
    async ({ skus, response_format }) => {
      try {
        const comparison = await api.compareProducts(skus);
        return toolResult(comparison, response_format, formatComparison(comparison));
      } catch (error) {
        return toolError(error);
      }
    },
  );

  server.registerTool(
    "salepilot_recommend_products",
    {
      title: "Recommend SalePilot Refrigerators",
      description:
        "Return a brand-diversified top-3 from currently priced refrigerators. Provide household_size or capacity_l plus budget_vnd; optional style, installation dimensions, and priorities refine the ranking.",
      inputSchema: z.object({
        household_size: z.number().int().min(1).max(20).optional(),
        capacity_l: z.number().int().min(1).max(2_000).optional(),
        budget_vnd: z.number().int().nonnegative().max(1_000_000_000).optional(),
        priorities: z
          .array(
            z.enum([
              "tiet_kiem_dien",
              "gia_re",
              "lay_nuoc_ngoai",
              "tu_dong",
              "dong_mem",
              "bao_quan",
              "dung_tich_lon",
            ]),
          )
          .max(7)
          .default([]),
        preferred_styles: z.array(z.string().trim().min(1).max(100)).max(5).default([]),
        max_width_cm: z.number().positive().max(500).optional(),
        max_height_cm: z.number().positive().max(500).optional(),
        max_depth_cm: z.number().positive().max(500).optional(),
        force: z.boolean().default(false),
        free_text: z.string().max(500).default(""),
        response_format: ResponseFormatSchema,
      }),
      outputSchema: RecommendationSchema,
      annotations: {
        readOnlyHint: true,
        destructiveHint: false,
        idempotentHint: true,
        openWorldHint: false,
      },
    },
    async ({ response_format, ...params }) => {
      try {
        const recommendation = await api.recommendProducts(params);
        return toolResult(recommendation, response_format, formatRecommendation(recommendation));
      } catch (error) {
        return toolError(error);
      }
    },
  );

  server.registerTool(
    "salepilot_search_faq",
    {
      title: "Search SalePilot Refrigerator Guidance",
      description:
        "Search refrigerator sizing, installation-space, pricing-source, preservation, and policy guidance. The knowledge base explicitly identifies facts absent from the source sheet.",
      inputSchema: z.object({
        query: z.string().max(200).default(""),
        limit: z.number().int().min(1).max(50).default(20),
        offset: z.number().int().nonnegative().default(0),
        response_format: ResponseFormatSchema,
      }),
      outputSchema: FaqPageSchema,
      annotations: {
        readOnlyHint: true,
        destructiveHint: false,
        idempotentHint: true,
        openWorldHint: false,
      },
    },
    async ({ response_format, ...params }) => {
      try {
        const page = await api.searchFaq(params);
        return toolResult(page, response_format, formatFaq(page));
      } catch (error) {
        return toolError(error);
      }
    },
  );

  server.registerTool(
    "salepilot_create_lead",
    {
      title: "Create a Confirmed SalePilot Lead",
      description:
        "Create a CRM lead only after the customer explicitly agrees to share contact information. Requires confirmed=true and a configured MCP write token; never infer consent.",
      inputSchema: z.object({
        confirmed: z.boolean().describe("True only after explicit customer confirmation."),
        name: z.string().trim().min(1).max(128).optional(),
        phone: z.string().trim().regex(/^[0-9+(). -]{8,32}$/),
        interest: z.string().trim().min(1).max(1_000),
        budget_vnd: z.number().int().nonnegative().max(1_000_000_000).optional(),
        notes: z.string().max(2_000).optional(),
        score: z.number().min(0).max(1).default(0.5),
        response_format: ResponseFormatSchema,
      }),
      outputSchema: LeadCreatedSchema,
      annotations: {
        readOnlyHint: false,
        destructiveHint: false,
        idempotentHint: false,
        openWorldHint: false,
      },
    },
    async ({ confirmed, response_format, ...params }) => {
      if (!confirmed) {
        return {
          content: [
            {
              type: "text" as const,
              text: "Lead was not created. Ask the customer for explicit consent, then call again with confirmed=true.",
            },
          ],
          isError: true,
        };
      }
      try {
        const lead = await api.createLead({ ...params, confirmed: true });
        return toolResult(lead, response_format, `## Lead created\n${lead.message}`);
      } catch (error) {
        return toolError(error);
      }
    },
  );
}
