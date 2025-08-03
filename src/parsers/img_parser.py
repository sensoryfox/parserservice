from __future__ import annotations

from io import BytesIO
from uuid import UUID, uuid4
from typing import List

from ..models import Line, ImageArtefact, ParseResult
from .base import BaseParser


class ImgParser(BaseParser):
    """Обрабатывает одиночный файл-картинку (png/jpg/…)."""

    async def parse(
        self,
        *,
        doc_id: UUID,
        file_content: BytesIO,
        parse_images: bool = True,
    ) -> ParseResult:
        img_bytes = file_content.read()
        key = f"{doc_id}/images/{uuid4().hex}.png"
        block_id = f"img/{uuid4().hex}"

        # Строка-заглушка (alt-текст будет добавлен позже)
        md_stub = f"![]({key})"

        lines = [
            Line(
                line_no=0,
                block_type="image",
                content=md_stub,
                block_id=block_id,
            )
        ]
        images = [
            ImageArtefact(
                key=key,
                data=img_bytes,
                source_block_id=block_id,
            )
        ]
        return ParseResult(lines=lines, images=images)