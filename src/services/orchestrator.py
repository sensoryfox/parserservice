from __future__ import annotations

import asyncio
from io import BytesIO
from pathlib import Path
from uuid import UUID
from redis.asyncio import Redis
import json
import traceback

from sensory_data_client import DataClient 
from ..adapters.llm_image import ImageDescriber
from ..models import Line
from ..parsers.base import BaseParser
from ..parsers.pdf_marker import PdfMarkerParser
from ..parsers.docx_parser import DocxParser
from ..parsers.xlsx_parser import XlsxParser
from ..parsers.txt_parser import TxtParser
from ..parsers.img_parser import ImgParser
from ..parsers.code_parser import CodeParser


class OrchestratorService:
    """Координирует процесс: скачать RAW → выбрать парсер → сохранить строки."""
    STAGES = ["DOWNLOADING", "PARSING", "ANALYZING_IMAGES", "SAVING"]

    def __init__(
        self,
        *,
        data_client: DataClient, # <-- Принимаем DataClient
        redis_client: Redis,
        llm: ImageDescriber | None = None,
    ):
        self._data_client = data_client # <-- Сохраняем его
        self._redis = redis_client
        self._llm = llm
        self._parsers = self._register_parsers()

    async def _set_status(
        self,
        doc_id: UUID,
        status: str,
        stage: str | None = None,
        error_message: str | None = None,
        result_data: dict | None = None
    ):
        """Устанавливает расширенный статус задачи в Redis."""
        key = f"parsing_status:{doc_id}"
        
        progress = 0.0
        if stage and status == "IN_PROGRESS":
            try:
                # Рассчитываем прогресс как долю пройденных стадий
                stage_index = self.STAGES.index(stage)
                progress = (stage_index + 1) / len(self.STAGES)
            except ValueError:
                progress = 0.0 # Неизвестная стадия
        elif status == "SUCCESS":
            progress = 1.0

        payload = {
            "status": status,
            "stage": stage,
            "progress": round(progress, 2), # Округляем до 2 знаков
            "error": error_message,
            "result": result_data,
        }
        # Удаляем ключи с None, чтобы не засорять Redis
        payload_cleaned = {k: v for k, v in payload.items() if v is not None}
        
        await self._redis.set(key, json.dumps(payload_cleaned), ex=3600)
    # -----------------------------------------------------------------
    def _register_parsers(self) -> dict[str, BaseParser]:
        """Регистрирует все доступные парсеры по расширениям файлов."""
        return {
            ".pdf": PdfMarkerParser(), ".pptx": PdfMarkerParser(),
            ".docx": DocxParser(),
            ".xlsx": XlsxParser(), ".xls": XlsxParser(),
            ".txt": TxtParser(), ".md": TxtParser(),
            ".png": ImgParser(), ".jpg": ImgParser(), ".jpeg": ImgParser(), ".gif": ImgParser(),
            ".py": CodeParser(), ".js": CodeParser(), ".ts": CodeParser(),
            ".c": CodeParser(), ".cpp": CodeParser(), ".go": CodeParser(), ".rs": CodeParser(),
        }

    # -----------------------------------------------------------------
    def _select_parser(self, file_name: str) -> BaseParser:
        ext = Path(file_name).suffix.lower()
        return self._parsers.get(ext, TxtParser())

    # -----------------------------------------------------------------
    async def process_document(
        self, doc_id: UUID, file_name: str, parse_images: bool = False
    ) -> None:
        """Полный конвейер обработки одного документа."""
        try:
            await self._set_status(doc_id, "IN_PROGRESS")
            print(f"[Orchestrator] Starting processing for doc_id={doc_id}, file_name='{file_name}'")

            # СТАДИЯ 1: DOWNLOADING
            await self._set_status(doc_id, "IN_PROGRESS", stage="DOWNLOADING")
            raw_bytes = await self._data_client.get_file(doc_id)
            
            # СТАДИЯ 2: PARSING
            await self._set_status(doc_id, "IN_PROGRESS", stage="PARSING")
            parser = self._select_parser(file_name)
            parse_result = await parser.parse(
                doc_id=doc_id, file_content=BytesIO(raw_bytes), parse_images=parse_images
            )
            
            # СТАДИЯ 3: ANALYZING_IMAGES
            if parse_images and parse_result.images and self._llm:
                await self._set_status(doc_id, "IN_PROGRESS", stage="ANALYZING_IMAGES")
                describe_tasks = [self._llm.describe(img.data) for img in parse_result.images]
                descriptions = await asyncio.gather(*describe_tasks, return_exceptions=True)
                
                for img, desc_or_exc in zip(parse_result.images, descriptions):
                    if isinstance(desc_or_exc, Exception):
                        print(f"Warning: Failed to get LLM description for image {img.key}: {desc_or_exc}")
                        continue
                    img.alt_text = desc_or_exc
                    # Обновляем MD-строку с alt-текстом
                    for line in parse_result.lines:
                        if line.block_id and line.block_id == img.source_block_id:
                            img_path_in_md = f"../images/{Path(img.key).name}"
                            line.content = f"![{img.alt_text}]({img_path_in_md})"
                            break

             # СТАДИЯ 4: SAVING
            await self._set_status(doc_id, "IN_PROGRESS", stage="SAVING")
            upload_tasks = [
                self._data_client.put_object(img.key, img.data, "image/png")
                for img in parse_result.images
            ]
            db_task = self._data_client.save_document_lines(doc_id, parse_result.lines)
            await asyncio.gather(db_task, *upload_tasks)

            # ФИНАЛ: SUCCESS
            result_summary = {
                "lines_count": len(parse_result.lines),
                "images_count": len(parse_result.images),
            }
            await self._set_status(doc_id, "SUCCESS", stage="SUCCESS", result_data=result_summary)
            print(f"[Orchestrator] Finished. Doc ID: {doc_id}. Success.")

        except Exception as e:
            # ФИНАЛ: FAILURE
            error_msg = f"{type(e).__name__}: {e}"
            traceback.print_exc()
            current_status_json = await self._redis.get(f"parsing_status:{doc_id}")
            current_stage = json.loads(current_status_json).get("stage") if current_status_json else "UNKNOWN"
            await self._set_status(doc_id, "FAILURE", stage=current_stage, error_message=error_msg)
            print(f"[Orchestrator] Finished. Doc ID: {doc_id}. Failure at stage {current_stage}.")