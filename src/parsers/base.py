from abc import ABC, abstractmethod
from io import BytesIO
from uuid import UUID
from typing import Protocol

from ..models import ParseResult


class BaseParser(ABC):
    """Абстрактный класс стратегии парсинга."""

    @abstractmethod
    async def parse(
        self,
        *,
        doc_id: UUID,
        file_content: BytesIO,
        parse_images: bool = True,
    ) -> ParseResult: ...