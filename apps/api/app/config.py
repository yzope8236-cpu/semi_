from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    clickhouse_host: str = "localhost"
    clickhouse_port: int = 8123
    clickhouse_user: str = "default"
    clickhouse_password: str = ""
    api_key: str = "change-me-for-production"
    cors_origins: str = "http://localhost:5173,http://localhost:8080"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
settings = Settings()
