# doc_parser_client.py
import asyncio
import httpx
from uuid import UUID, uuid4
from pydantic import BaseModel, Field

# Эти модели дублируют модели с сервера для удобства и валидации
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
    
class DocParserError(Exception):
    """Ошибка во время парсинга на удаленном сервисе."""
    def __init__(self, message, doc_id):
        self.message = message
        self.doc_id = doc_id
        super().__init__(f"Parsing failed for doc {doc_id}: {message}")

class DocParserClient:
    """Асинхронный клиент для взаимодействия с сервисом doc-parser."""

    def __init__(self, base_url: str, timeout: float = 30.0):
        self.base_url = base_url
        self.timeout = timeout

    async def start_parsing(self, doc_id: UUID, file_name: str, parse_images: bool = True) -> StatusResponse:
        """Отправляет задачу на парсинг и не ждет ее завершения."""
        async with httpx.AsyncClient() as client:
            req = ParseRequest(file_name=file_name, parse_images=parse_images)
            response = await client.post(
                f"{self.base_url}/parse/{doc_id}",
                json=req.model_dump(),
                timeout=self.timeout
            )
            response.raise_for_status()
            return StatusResponse.model_validate(response.json())

    async def get_status(self, doc_id: UUID) -> StatusResponse:
        """Получает текущий статус задачи."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/parse/status/{doc_id}", timeout=self.timeout)
            response.raise_for_status()
            return StatusResponse.model_validate(response.json())

    async def parse_and_wait(
        self,
        doc_id: UUID,
        file_name: str,
        parse_images: bool = False,
        poll_interval: float = 2.0,
        timeout: float = 300.0
    ) -> dict:
        """
        Главный метод: отправляет задачу, ждет ее завершения и возвращает результат.
        """
        start_time = asyncio.get_event_loop().time()
        
        print(f"Client: Starting parsing for doc_id={doc_id}, file_name='{file_name}'...")
        await self.start_parsing(doc_id, file_name, parse_images)
        
        while True:
            if asyncio.get_event_loop().time() - start_time > timeout:
                raise asyncio.TimeoutError(f"Parsing timed out after {timeout} seconds for doc {doc_id}")
            
            await asyncio.sleep(poll_interval)
            status_res = await self.get_status(doc_id)
            
            # Формируем красивое сообщение о прогрессе
            progress_percent = int((status_res.progress or 0) * 100)
            stage_info = f" | Stage: {status_res.stage}" if status_res.stage else ""
            print(f"Client: Polling status for {doc_id}... [{progress_percent:3d}%] {status_res.status}{stage_info}")
            
            if status_res.status == "SUCCESS":
                print(f"Client: Parsing for {doc_id} completed successfully.")
                return status_res.result or {}
            
            if status_res.status == "FAILURE":
                raise DocParserError(status_res.error, doc_id)

async def main():
    # Предполагается, что search-api загрузил файл в MinIO
    # и теперь запускает парсинг.
    
    DOC_ID = uuid4()
    FILE_NAME = "my_financial_report.pdf"
    PARSER_URL = "http://localhost:8000" # URL нашего doc-parser сервиса
    
    # 1. Загрузить файл в MinIO... (эта логика в search-api)
    # await data_client.put_object(f"{DOC_ID}/raw/{FILE_NAME}", b"...")
    
    # 2. Запустить парсинг и дождаться результата
    parser_client = DocParserClient(base_url=PARSER_URL)
    try:
        result = await parser_client.parse_and_wait(doc_id=DOC_ID, file_name=FILE_NAME)
        print("\n--- Final Result ---")
        print(result) # -> {'lines_count': 150, 'images_count': 3}
    except (DocParserError, asyncio.TimeoutError) as e:
        print(f"\n--- Error --- \n{e}")

if __name__ == "__main__":
    asyncio.run(main())