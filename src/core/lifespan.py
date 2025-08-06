# src/core/lifespan.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from sensory_data_client import create_data_client, get_settings, DataClientConfig, PostgresConfig, MinioConfig
from ..adapters.llm_image import ImageDescriber
from ..services.orchestrator import OrchestratorService
from .config import settings
import redis.asyncio as aioredis

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Initializing services...")
    redis_client = aioredis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
    app.state.redis = redis_client
    # Создаем один экземпляр DataClient на все приложение
    # Он сам должен подхватить свои настройки из env
    
    
    data_client = create_data_client(DataClientConfig(minio=MinioConfig(endpoint="localhost:9008", bucket='documents')) 
)
    print(get_settings())
    
    # Инициализируем адаптер для LLM
    llm_adapter = ImageDescriber(
        api_url=settings.llm_image_api_url, 
        api_key=settings.llm_image_api_key
    ) if settings.llm_image_api_url else None
    
    # Внедряем зависимости в сервис-оркестратор
    app.state.orchestrator = OrchestratorService(
        data_client=data_client,
        llm=llm_adapter,
        redis_client=redis_client # <-- Передаем клиент в сервис
    )

    yield

    print("Cleaning up resources...")
    await app.state.redis.close()