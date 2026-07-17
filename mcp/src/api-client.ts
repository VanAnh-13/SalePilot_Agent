import { z } from "zod";

export const ProductSchemaOutput = z
  .object({
    sku: z.string(),
    name: z.string(),
    category_code: z.literal(38),
    price_vnd: z.number().nullable(),
    price_display: z.string(),
    style: z.string().nullable(),
    usable_capacity_l: z.number().nullable(),
  })
  .passthrough();

export const ProductPageSchema = z
  .object({
    items: z.array(ProductSchemaOutput),
    total_count: z.number().int().nonnegative(),
    count: z.number().int().nonnegative(),
    offset: z.number().int().nonnegative(),
    has_more: z.boolean(),
    next_offset: z.number().int().nonnegative().nullable(),
  })
  .passthrough();

export const ComparisonSchema = z
  .object({
    ok: z.boolean(),
    items: z.array(ProductSchemaOutput),
    tradeoffs: z.array(z.string()).default([]),
    plain_summary: z.string().optional(),
    source: z.string(),
  })
  .passthrough();
export const RecommendationSchema = z
  .object({
    ok: z.boolean(),
    need_more: z.boolean().optional(),
    message: z.string().optional(),
    top3: z.array(ProductSchemaOutput).optional(),
    tradeoffs: z.array(z.string()).optional(),
    ask: z.array(z.string()).optional(),
    source: z.string(),
  })
  .passthrough();
const FaqSchema = z.object({
  id: z.string(),
  question: z.string(),
  answer: z.string(),
});
export const FaqPageSchema = z
  .object({
    items: z.array(FaqSchema),
    total_count: z.number().int().nonnegative(),
    count: z.number().int().nonnegative(),
    offset: z.number().int().nonnegative(),
    has_more: z.boolean(),
    next_offset: z.number().int().nonnegative().nullable(),
  })
  .passthrough();
export const LeadCreatedSchema = z.object({
  lead_id: z.number().int().positive(),
  status: z.string(),
  score: z.number(),
  message: z.string(),
});

export type ProductPage = z.infer<typeof ProductPageSchema>;
export type Product = z.infer<typeof ProductSchemaOutput>;
export type Comparison = z.infer<typeof ComparisonSchema>;
export type Recommendation = z.infer<typeof RecommendationSchema>;
export type FaqPage = z.infer<typeof FaqPageSchema>;
export type LeadCreated = z.infer<typeof LeadCreatedSchema>;

export class SalePilotApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "SalePilotApiError";
  }
}

type QueryValue = string | number | boolean | undefined;

export class SalePilotApiClient {
  private readonly baseUrl: URL;
  private readonly writeToken: string;

  constructor(
    baseUrl = process.env.SALEPILOT_API_BASE_URL ?? "http://127.0.0.1:8000",
    writeToken = process.env.SALEPILOT_MCP_WRITE_TOKEN ?? "",
  ) {
    const parsedUrl = new URL(baseUrl);
    if (!["http:", "https:"].includes(parsedUrl.protocol)) {
      throw new Error("SALEPILOT_API_BASE_URL must use http or https.");
    }
    if (parsedUrl.username || parsedUrl.password) {
      throw new Error("SALEPILOT_API_BASE_URL must not include credentials.");
    }

    const localHosts = new Set(["127.0.0.1", "localhost", "::1", "[::1]"]);
    if (!localHosts.has(parsedUrl.hostname) && process.env.SALEPILOT_ALLOW_REMOTE_API !== "true") {
      throw new Error(
        "Refusing a non-local SalePilot API. Set SALEPILOT_ALLOW_REMOTE_API=true only for a trusted endpoint.",
      );
    }

    parsedUrl.pathname = `${parsedUrl.pathname.replace(/\/+$/, "")}/`;
    this.baseUrl = parsedUrl;
    this.writeToken = writeToken;
  }

  async searchProducts(params: {
    query?: string;
    budget_vnd?: number;
    household_size?: number;
    min_capacity_l?: number;
    max_width_cm?: number;
    max_height_cm?: number;
    max_depth_cm?: number;
    energy_saving?: boolean;
    brand?: string;
    style?: string;
    priced_only?: boolean;
    limit?: number;
    offset?: number;
  }): Promise<ProductPage> {
    return this.get("mcp/products", params, ProductPageSchema);
  }

  async getProduct(sku: string): Promise<Product> {
    return this.get(`mcp/products/${encodeURIComponent(sku)}`, {}, ProductSchemaOutput);
  }

  async compareProducts(skus: string[]): Promise<Comparison> {
    return this.post("mcp/product-comparisons", { skus }, ComparisonSchema);
  }

  async recommendProducts(params: {
    household_size?: number;
    capacity_l?: number;
    budget_vnd?: number;
    priorities?: string[];
    preferred_styles?: string[];
    max_width_cm?: number;
    max_height_cm?: number;
    max_depth_cm?: number;
    force?: boolean;
    free_text?: string;
  }): Promise<Recommendation> {
    return this.post("mcp/recommendations", params, RecommendationSchema);
  }

  async searchFaq(params: { query?: string; limit?: number; offset?: number }): Promise<FaqPage> {
    return this.get("mcp/knowledge/faq", params, FaqPageSchema);
  }

  async createLead(params: {
    confirmed: true;
    name?: string;
    phone: string;
    interest: string;
    budget_vnd?: number;
    notes?: string;
    score?: number;
  }): Promise<LeadCreated> {
    return this.post("mcp/leads", params, LeadCreatedSchema, this.writeToken);
  }

  private async get<T>(
    path: string,
    query: Record<string, QueryValue>,
    schema: z.ZodType<T>,
  ): Promise<T> {
    const url = new URL(path, this.baseUrl);
    for (const [key, value] of Object.entries(query)) {
      if (value !== undefined && value !== "") {
        url.searchParams.set(key, String(value));
      }
    }
    return this.request(url, { method: "GET" }, schema);
  }

  private async post<T>(
    path: string,
    body: unknown,
    schema: z.ZodType<T>,
    token = "",
  ): Promise<T> {
    const headers: Record<string, string> = { "content-type": "application/json" };
    if (token) {
      headers["x-salepilot-mcp-token"] = token;
    }
    return this.request(
      new URL(path, this.baseUrl),
      { method: "POST", headers, body: JSON.stringify(body) },
      schema,
    );
  }

  private async request<T>(
    url: URL,
    init: RequestInit,
    schema: z.ZodType<T>,
  ): Promise<T> {
    let response: Response;
    try {
      response = await fetch(url, { ...init, signal: AbortSignal.timeout(10_000) });
    } catch {
      throw new SalePilotApiError(
        0,
        `Cannot reach SalePilot at ${this.baseUrl.origin}. Start the backend or set SALEPILOT_API_BASE_URL.`,
      );
    }

    const raw = await response.text();
    let payload: unknown = null;
    if (raw) {
      try {
        payload = JSON.parse(raw);
      } catch {
        throw new SalePilotApiError(response.status, "SalePilot returned a non-JSON response.");
      }
    }
    if (!response.ok) {
      const detail =
        payload && typeof payload === "object" && "detail" in payload
          ? String(payload.detail)
          : `SalePilot returned HTTP ${response.status}.`;
      throw new SalePilotApiError(response.status, detail);
    }

    const parsed = schema.safeParse(payload);
    if (!parsed.success) {
      throw new SalePilotApiError(
        response.status,
        "SalePilot returned an unexpected response. Check that the backend MCP API is up to date.",
      );
    }
    return parsed.data;
  }
}
