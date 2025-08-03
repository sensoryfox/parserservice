from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """Читает переменные окружения из .env файла."""
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    redis_url: str = "redis://localhost:6379/0"
    # Настройки для LLM-сервиса описания изображений
    llm_image_api_url: str | None = None
    llm_image_api_key: str | None = None

settings = Settings()