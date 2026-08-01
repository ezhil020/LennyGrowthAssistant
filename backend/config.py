"""
config.py — Application settings with startup validation.

All configuration is read from environment variables (via .env file).
The app refuses to start with a clear, human-readable error if required
settings are missing or incompatible.
"""

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Database ──────────────────────────────────────────────
    database_url: str

    # ── LLM Providers ────────────────────────────────────────
    active_llm_provider: str = "anthropic"  # "anthropic" | "ollama"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-3-5-sonnet-20241022"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"

    # ── Embeddings ───────────────────────────────────────────
    active_embedding_model: str = "ollama"  # "ollama" | "openai"
    openai_api_key: str = ""

    # ── Retrieval ────────────────────────────────────────────
    retrieval_mode: str = "hybrid"  # "hybrid" | "vector" | "lexical"
    retrieval_top_k: int = 8

    # ── Context Window ───────────────────────────────────────
    context_window_threshold: float = 0.8  # summarise at 80% of model max tokens

    # ── Rate Limiting ────────────────────────────────────────
    rate_limit_per_minute: int = 60

    # ── Ingestion ────────────────────────────────────────────
    transcript_repo_url: str = (
        "https://github.com/ChatPRD/lennys-podcast-transcripts"
    )
    ingest_limit: int = 50  # 0 = ingest all

    # ── Derived helpers ──────────────────────────────────────
    @property
    def anthropic_max_tokens(self) -> int:
        """Context limit for the configured Anthropic model."""
        limits = {
            "claude-3-5-sonnet-20241022": 200_000,
            "claude-3-opus-20240229": 200_000,
            "claude-3-haiku-20240307": 200_000,
        }
        return limits.get(self.anthropic_model, 100_000)

    @property
    def ollama_max_tokens(self) -> int:
        """Conservative context limit for local Ollama models."""
        return 8_192

    @property
    def active_provider_max_tokens(self) -> int:
        if self.active_llm_provider == "anthropic":
            return self.anthropic_max_tokens
        return self.ollama_max_tokens

    # ── Startup validation ───────────────────────────────────
    @model_validator(mode="after")
    def validate_provider_config(self) -> "Settings":
        if self.active_llm_provider == "anthropic" and not self.anthropic_api_key:
            raise ValueError(
                "\n\n  ✗ ANTHROPIC_API_KEY is required when ACTIVE_LLM_PROVIDER=anthropic.\n"
                "    Set it in your .env file or as an environment variable.\n"
                "    Example: ANTHROPIC_API_KEY=sk-ant-...\n"
            )
        if self.active_llm_provider not in ("anthropic", "ollama"):
            raise ValueError(
                f"\n\n  ✗ Unknown ACTIVE_LLM_PROVIDER: '{self.active_llm_provider}'.\n"
                "    Valid values: 'anthropic', 'ollama'\n"
            )
        if self.active_embedding_model == "openai" and not self.openai_api_key:
            raise ValueError(
                "\n\n  ✗ OPENAI_API_KEY is required when ACTIVE_EMBEDDING_MODEL=openai.\n"
                "    Set it in your .env file or as an environment variable.\n"
            )
        if self.active_embedding_model not in ("ollama", "openai"):
            raise ValueError(
                f"\n\n  ✗ Unknown ACTIVE_EMBEDDING_MODEL: '{self.active_embedding_model}'.\n"
                "    Valid values: 'ollama', 'openai'\n"
            )
        if self.retrieval_mode not in ("hybrid", "vector", "lexical"):
            raise ValueError(
                f"\n\n  ✗ Unknown RETRIEVAL_MODE: '{self.retrieval_mode}'.\n"
                "    Valid values: 'hybrid', 'vector', 'lexical'\n"
            )
        return self


# Singleton — import this everywhere
settings = Settings()
