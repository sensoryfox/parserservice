from __future__ import annotations

from io import BytesIO
from uuid import UUID
from typing import List

from ..models import Line, ParseResult
from .base import BaseParser


class TxtParser(BaseParser):
    """Самый простой: каждая строка – текст."""

    async def parse(
        self,
        *,
        doc_id: UUID,          # не используется
        file_content: BytesIO,
        parse_images: bool = True,  # нет изображений
    ) -> ParseResult:
        content = file_content.read().decode("utf-8", errors="replace")
        lines_raw = content.splitlines()

        lines: List[Line] = [
            Line(line_no=i, block_type="text", content=txt)
            for i, txt in enumerate(lines_raw)
        ]
        return ParseResult(lines=lines, images=[])