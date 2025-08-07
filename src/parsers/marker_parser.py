# В файле parsers/marker_parser.py

import asyncio
from io import BytesIO
from uuid import UUID, uuid4
from typing import List, Dict, Any

from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict
from marker.config.parser import ConfigParser as MarkerConfigParser

from ..models import ParseResult, Line, ImageArtefact
from .base import BaseParser
from ..core.config import MarkerSettings # Импортируем нашу модель настроек

class UnifiedMarkerParser(BaseParser):
    def __init__(self):
        self.settings = MarkerSettings()
        # Предварительно создаем модели один раз, это может быть ресурсоемко
        self._model_dict = create_model_dict()

    async def parse(
        self,
        *,
        doc_id: UUID,
        file_content: BytesIO,
        parse_images: bool = True, # Этот флаг может управляться настройками
    ) -> ParseResult:
        # 1. Создаем конфигурацию и конвертер для Marker
        # MarkerConfigParser позволяет передать словарь настроек
        config_parser = MarkerConfigParser(self.settings.model_dump())
        
        converter = PdfConverter(
            config=config_parser.generate_config_dict(),
            artifact_dict=self._model_dict,
            # Сюда можно передать и другие объекты, если нужно (llm_service и т.д.)
        )

        # 2. Выполняем синхронный вызов в отдельном потоке
        rendered_doc = await asyncio.get_event_loop().run_in_executor(
            None, converter, file_content
        )

        # 3. Обрабатываем результат (это будет JSON-дерево)
        lines: List[Line] = []
        images: List[ImageArtefact] = []
        
        # Рекурсивно обходим дерево блоков
        print("*"*80)
        print(rendered_doc)
        self._process_marker_blocks(
            doc_id=doc_id,
            blocks=rendered_doc, 
            lines=lines, 
            images=images,
            parse_images=parse_images
        )
        
        # Сортируем строки, т.к. рекурсивный обход не гарантирует порядок
        lines.sort(key=lambda line: line.line_no)

        return ParseResult(lines=lines, images=images)

    def _process_marker_blocks(
        self, doc_id: UUID, blocks: List[Any], lines: List[Line], images: List[ImageArtefact], parse_images: bool
    ):
        """Рекурсивно обходит JSON-дерево от Marker и наполняет наши модели Line и Image."""
        for block in blocks:
            page_idx = self._get_page_index(block.id)
            
            # Если это блок с картинкой
            if block.block_type == "Figure" and parse_images and block.images:
                for img_id, img_data in block.images.items():
                    key = f"{doc_id}/images/{uuid4().hex}.png"
                    images.append(ImageArtefact(key=key, data=img_data, source_block_id=img_id))
                    # Добавляем MD-заглушку для изображения
                    md_stub = f"![]({key})"
                    lines.append(Line(
                        line_no=len(lines), # Временный line_no
                        page_idx=page_idx,
                        block_type="image",
                        content=md_stub,
                        block_id=img_id,
                        coordinates=block.polygon,
                    ))

            # Если это текстовый блок (параграф, заголовок, элемент списка и т.д.)
            elif hasattr(block, "text_with_inline_math"):
                text_lines = block.text_with_inline_math.splitlines()
                for text in text_lines:
                    if not text.strip(): continue
                    lines.append(Line(
                        line_no=len(lines), # Временный line_no
                        page_idx=page_idx,
                        block_type=block.block_type, # "Text", "SectionHeader", "ListItem"
                        content=text,
                        block_id=block.id,
                        coordinates=block.polygon,
                    ))
            
            # Если у блока есть дочерние элементы, идем вглубь
            if block.children:
                self._process_marker_blocks(doc_id, block.children, lines, images, parse_images)
    
    def _get_page_index(self, block_id: str) -> int | None:
        """Извлекает номер страницы из ID блока (например, '/page/10/...')."""
        parts = block_id.split('/')
        if len(parts) > 2 and parts[1] == 'page':
            try:
                return int(parts[2])
            except (ValueError, IndexError):
                return None
        return None