from functools import lru_cache
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from emiva_core.core.llm_providers import Provider


class Settings(BaseSettings):
    project_name: str = "GTM Pack Generator"
    version: str = "1.0.0"
    debug: bool = False
    environment: str = "development"
    enable_phoenix: bool = True

    postgres_user: str = "emiva-user"
    postgres_password: str = ""
    postgres_db: str = "emiva-db"
    postgres_host: str = "localhost"
    postgres_port: int = 5432

    @property
    def database_url(self) -> str:
        return f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    llm_provider: str | None = None
    llm_model_name: str | None = None

    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    groq_api_key: str | None = None

    default_openai_model: str = "gpt-4o"
    default_anthropic_model: str = (
        "claude-3-5-sonnet-20241022"  # TODO: Verify this model name exists
    )
    default_groq_model: str = "llama-3.3-70b-versatile"

    temperature: float = 0.7

    @model_validator(mode="before")
    @classmethod
    def validate_llm_provider_and_key(cls, values):
        provider = values.get("llm_provider")
        if not provider:
            return values

        supported_providers = [p.value for p in Provider]
        if provider not in supported_providers:
            raise ValueError(
                f"Unsupported LLM provider '{provider}'. Must be one of: {supported_providers}"
            )

        key_map = {
            Provider.OPENAI.value: ("openai_api_key", "OPENAI_API_KEY"),
            Provider.ANTHROPIC.value: ("anthropic_api_key", "ANTHROPIC_API_KEY"),
            Provider.GROQ.value: ("groq_api_key", "GROQ_API_KEY"),
        }

        field, env_var = key_map[provider]
        if not values.get(field):
            raise ValueError(f"{env_var} must be set when llm_provider is '{provider}'")

        return values

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
