from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    llm_provider: str = "openai"
    openai_api_key: str = ""
    # Optional: point the OpenAI client at an OpenAI-compatible endpoint
    # (Groq, Together, OpenRouter, DeepSeek, vLLM, Ollama, LM Studio, ...).
    # Empty = official OpenAI API.
    openai_base_url: str = ""
    anthropic_api_key: str = ""
    model_name: str = "gpt-4o-mini"
    # Latency guards: cap reply length + per-request timeout (seconds).
    llm_max_tokens: int = 700
    # Per-request LLM timeout. Kept tight so an unreachable/slow endpoint degrades
    # to the friendly fallback quickly instead of hanging the chat; 30s is ample
    # for a max_tokens-capped reply on a healthy endpoint.
    llm_timeout_s: int = 30
    # Fast-path: False = instant, deterministic Markdown top-3 (structured,
    # source-grounded, no LLM call) — the default, and what the chat UI renders
    # best. True = spend 1 LLM call to rephrase as prose (slower, and burns the
    # shared token budget the full graph needs). Flip to True only when the LLM
    # endpoint is fast and you specifically want conversational phrasing.
    fast_path_phrasing: bool = False

    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    # PostgreSQL — primary relational store (CRM, catalog mirror, KB).
    # Async URL (asyncpg) for the app; sync DSN (psycopg2) for the catalog
    # ranking path and the ETL scripts. Both point at the same database.
    database_url: str = "postgresql+asyncpg://salepilot:salepilot@localhost:5433/salepilot"
    postgres_dsn: str = "postgresql+psycopg2://salepilot:salepilot@localhost:5433/salepilot"
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    chroma_path: str = "./data/chroma"
    mcp_write_token: str = ""
    # Admin API protection — set to a strong random token in production.
    # Empty string means admin endpoints will return 403 to all callers.
    admin_api_key: str = ""

    # Catalog source priority: Postgres primary, MongoDB secondary, JSON snapshot last.
    catalog_backend: str = "postgres"  # postgres | mongodb | snapshot

    # MongoDB — secondary/document catalog store (all product categories).
    mongodb_uri: str = "mongodb://salepilot:salepilot@localhost:27017/salepilot?authSource=admin"
    mongodb_db: str = "salepilot"
    mongodb_products_collection: str = "products"
    # When both databases are unreachable the repository falls back to this snapshot.
    catalog_snapshot: str = "./data/catalog_snapshot.json"

    # Path to the DMX crawl data directory (products_detail.json + policy .md files).
    # Set this in .env or via the DMX_SRC_DIR environment variable.
    # Scripts that need raw DMX data read this value; no path is hardcoded in code.
    dmx_src_dir: str = ""


    zalo_enabled: bool = True
    zalo_client: str = "mock"
    zalo_oa_access_token: str = ""
    zalo_oa_secret: str = ""
    zalo_webhook_secret: str = ""
    # Default: strict — rejects any webhook payload without a valid HMAC-SHA256
    # signature.  Set to "off" only in development / mock environments.
    zalo_verify_mode: str = "strict"

    shop_name: str = "SalePilot Điện Máy"
    # Default category slug used when the user's intent is ambiguous.
    shop_category: str = "tu_lanh"

    memory_enabled: bool = True
    auto_skill_write: bool = False
    sandbox_enabled: bool = True
    # Disabled by default to prevent SSRF in shared/production deployments.
    # Enable explicitly in .env when the fetch tool is needed.
    web_fetch_enabled: bool = False
    scheduler_enabled: bool = True
    max_subagents_per_turn: int = 3
    trajectory_enabled: bool = True

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
