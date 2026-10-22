from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    llm_provider: str = "gemini"
    gemini_api_key: str = ""
    gemini_chat_model: str = "gemini-3.5-flash-lite"
    gemini_embed_model: str = "gemini-embedding-001"
    embed_dim: int = 768

    database_url: str = ""

    company_name: str = "Fernbill"
    sample_docs_dir: str = "sample_docs/fernbill"

    top_k: int = 5
    min_similarity: float = 0.45
    max_chunk_chars: int = 1200

    admin_token: str = ""
    cors_origins: str = "http://localhost:3000"

    # Questions per minute per visitor. Protects a free-tier API key on a public demo.
    chat_rate_limit: int = 12
    # Pause between eval questions so a full run stays under free-tier rate limits.
    eval_delay_seconds: float = 6.0
    # Show the documentation-gaps page without an admin token. Off by default because
    # it lists whatever visitors typed.
    public_dashboard: bool = False

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
