from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    llm_provider: str = "openai"
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    model_name: str = "gpt-4o-mini"

    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    database_url: str = "sqlite+aiosqlite:///./data/salepilot.db"
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    chroma_path: str = "./data/chroma"
    mcp_write_token: str = ""

    zalo_enabled: bool = True
    zalo_client: str = "mock"
    zalo_oa_access_token: str = ""
    zalo_oa_secret: str = ""
    zalo_webhook_secret: str = ""
    zalo_verify_mode: str = "off"

    shop_name: str = "SalePilot Điện Máy"
    shop_category: str = "tu_lanh"

    memory_enabled: bool = True
    auto_skill_write: bool = False
    sandbox_enabled: bool = True
    web_fetch_enabled: bool = True
    scheduler_enabled: bool = True
    max_subagents_per_turn: int = 3
    trajectory_enabled: bool = True

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
