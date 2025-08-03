# src/main.py
import json
from uuid import UUID
from fastapi import FastAPI, BackgroundTasks, HTTPException, Request
from pydantic import BaseModel
from .core.lifespan import lifespan
from .services.orchestrator import OrchestratorService

app = FastAPI(
    title="Document Parser Service",
    description="A stateless service to parse documents and store artefacts.",
    lifespan=lifespan
)

class ParseRequest(BaseModel):
    file_name: str
    parse_images: bool = True
    
class StatusResponse(BaseModel):
    doc_id: UUID
    status: str  # PENDING, IN_PROGRESS, SUCCESS, FAILURE
    stage: str | None = None  # QUEUED, DOWNLOADING, PARSING, etc.
    progress: float | None = None # Число от 0.0 до 1.0
    error: str | None = None
    result: dict | None = None


@app.post("/parse/{doc_id}", status_code=202, response_model=StatusResponse)
async def start_parsing(doc_id: UUID, request_data: ParseRequest, r: Request, background_tasks: BackgroundTasks):
    """
    Принимает запрос на парсинг, создает задачу и немедленно возвращает ее текущий статус.
    """
    orchestrator: OrchestratorService = r.app.state.orchestrator
    redis_client = r.app.state.redis

    # Устанавливаем первоначальный статус PENDING
    initial_status = {"status": "PENDING", "stage": "QUEUED", "progress": 0.0}
    await redis_client.set(f"parsing_status:{doc_id}", json.dumps(initial_status), ex=3600)

    background_tasks.add_task(
        orchestrator.process_document,
        doc_id=doc_id,
        file_name=request_data.file_name,
        parse_images=request_data.parse_images
    )
    
    return StatusResponse(doc_id=doc_id, status="PENDING", stage="QUEUED", progress=0.0)

@app.get("/parse/status/{doc_id}", response_model=StatusResponse)
async def get_parsing_status(doc_id: UUID, r: Request):
    """Возвращает текущий статус задачи парсинга."""
    redis_client = r.app.state.redis
    status_json = await redis_client.get(f"parsing_status:{doc_id}")
    
    if not status_json:
        raise HTTPException(status_code=404, detail=f"Parsing task for document {doc_id} not found.")
        
    status_data = json.loads(status_json)
    return StatusResponse(doc_id=doc_id, **status_data)

@app.get("/healthz", tags=["Monitoring"])
def health_check():
    """Простая проверка работоспособности сервиса."""
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    # Это позволит запускать приложение напрямую для отладки
    # Убедитесь, что Redis и другие сервисы доступны по localhost
    print("Starting server locally in debug mode...")
    print("Make sure Redis, Postgres, MinIO are running and accessible on localhost.")
    print("Update your .env file to point to localhost ports (e.g., redis://localhost:6379).")
    
    uvicorn.run(app, host="127.0.0.1", port=8000)