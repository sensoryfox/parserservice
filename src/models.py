from pydantic import BaseModel, Field
from uuid import UUID

class ImageArtefact(BaseModel):
    # Уникальный ключ объекта в MinIO. Формат: {doc_id}/images/{uuid}.png
    key: str
    # Содержимое файла в памяти
    data: bytes = Field(repr=False)
    # Описание, полученное от LLM
    alt_text: str | None = None
    # ID блока, где это изображение было найдено. Нужно для обновления строки.
    source_block_id: str | None = None

class Line(BaseModel):
    # Поля, которые напрямую пишутся в DocumentLineORM
    line_no: int
    page_idx: int | None = None
    sheet_name: str | None = None
    block_type: str
    content: str
    block_id: str | None = None

class ParseResult(BaseModel):
    lines: list[Line]
    images: list[ImageArtefact]
    warnings: list[str] = []