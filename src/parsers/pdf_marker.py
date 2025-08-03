from __future__ import annotations

import asyncio
from io import BytesIO
from uuid import UUID, uuid4
from typing import Dict, Any, List

from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict
from marker.output import text_from_rendered

from ..models import ParseResult, Line, ImageArtefact
from .base import BaseParser


def _build_block_map(meta: Dict[str, Any]) -> Dict[int, Dict[str, Any]]:
    """
    На основе marker-metadata строим карту:
      line_idx -> {"block_id": str, "block_type": str, "page_idx": int}
    В реальной жизни имеет смысл хранить её в MinIO,
    но здесь – простая проекция (Marker даёт page_stats и html-offsets).
    """
    line_map: Dict[int, Dict[str, Any]] = {}
    pages: List[Dict[str, Any]] = meta.get("page_stats", [])
    for page in pages:
        page_idx = page.get("page_id")
        # block_counts: List[("Span", 120), ...] – здесь нет координат строк,
        # поэтому используем упрощённую логику: каждая строка подряд на странице.
        # В meta есть более точная информация (children-tree), но это «минималка».
    # Возвращаем пустую map – типы будут Unknown, но это безопасно.
    return line_map


class PdfMarkerParser(BaseParser):
    """
    Парсер для PDF и PPTX.
    PPTX Marker конвертирует в PDF «на лету».
    """

    async def parse(
        self,
        *,
        doc_id: UUID,
        file_content: BytesIO,
        parse_images: bool = True,
    ) -> ParseResult:
        converter = PdfConverter(artifact_dict=create_model_dict())
        # Marker – синхронный, поэтому вне главного цикла
        rendered = await asyncio.get_event_loop().run_in_executor(
            None, converter, file_content  # type: ignore[arg-type]
        )

        md_text, meta, m_images = text_from_rendered(rendered)
        md_lines = md_text.splitlines()

        block_map = _build_block_map(meta)

        lines: List[Line] = []
        for idx, text in enumerate(md_lines):
            bm = block_map.get(idx, {})
            lines.append(
                Line(
                    line_no=idx,
                    page_idx=bm.get("page_idx"),
                    block_type=bm.get("block_type", "unknown"),
                    content=text,
                    block_id=bm.get("block_id"),
                )
            )

        images: List[ImageArtefact] = []
        if parse_images and m_images:
            for img in m_images:
                key = f"{doc_id}/images/{uuid4().hex}.png"
                images.append(
                    ImageArtefact(
                        key=key,
                        data=img.data,
                        source_block_id=img.id,
                    )
                )

        return ParseResult(lines=lines, images=images)