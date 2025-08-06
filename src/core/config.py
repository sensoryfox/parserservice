from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import BaseModel, Field

class MarkerSettings(BaseModel):
    """Настройки для движка Marker"""
    output_format: str = "json" # <-- Всегда используем JSON!
    force_ocr: bool = False
    use_llm: bool = False
    # Добавьте другие важные для вас флаги из документации Marker
    # Например, для подключения к Ollama или Gemini
    llm_service: str | None = None # "marker.services.ollama.OllamaService"
    ollama_model: str | None = "llama3"
    ollama_base_url: str | None = "http://localhost:11434"


class Settings(BaseSettings):
    """Читает переменные окружения из .env файла."""
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    redis_url: str = "redis://localhost:6379/0"
    # Настройки для LLM-сервиса описания изображений
    llm_image_api_url: str | None = None
    llm_image_api_key: str | None = None
    marker: MarkerSettings = Field(default_factory=MarkerSettings)
    model_config = SettingsConfigDict(
        env_file=".env", 
        extra="ignore",
        # Позволяет задавать вложенные переменные окружения, например:
        # MARKER_FORCE_OCR=true
        env_nested_delimiter='_'
    )

    
    
settings = Settings()