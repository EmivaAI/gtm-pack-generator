from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    project_name: str = "GTM Pack Generator"
    debug: bool = False
    environment: str = "development"
    
    postgres_user: str = "emiva-user"
    postgres_password: str = ""
    postgres_db: str = "emiva-db"
    postgres_host: str = "localhost"
    postgres_port: int = 5432

    @property
    def database_url(self) -> str:
        return f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
    
    llm_provider: str = ""
    llm_api_key: str = ""
    llm_base_url: str = ""
    model_name: str = ""
    temperature: float = 0.7
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

@lru_cache
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
