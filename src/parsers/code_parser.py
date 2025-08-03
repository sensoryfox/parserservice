from __future__ import annotations

import re
from io import BytesIO
from uuid import UUID
from typing import List

from ..models import Line, ParseResult
from .base import BaseParser


_IMPORT_RE = re.compile(r"^\s*(import|from)\s+")
_DEF_RE = re.compile(r"^\s*(def|class)\s+")
_COMMENT_RE = re.compile(r"^\s*(#|//|/\*)")


class CodeParser(BaseParser):
    """
    Универсальный парсер исходного кода.
    Выделяет block_type: import / def / class / comment / code.
    """

    async def parse(
        self,
        *,
        doc_id: UUID,          # не используется
        file_content: BytesIO,
        parse_images: bool = True,  # нет изображений
    ) -> ParseResult:
        text = file_content.read().decode("utf-8", errors="replace")
        raw_lines = text.splitlines()

        lines: List[Line] = []
        for idx, src in enumerate(raw_lines):
            if _IMPORT_RE.match(src):
                btype = "import"
            elif _DEF_RE.match(src):
                btype = "definition"
            elif _COMMENT_RE.match(src):
                btype = "comment"
            else:
                btype = "code"
            lines.append(Line(line_no=idx, block_type=btype, content=src))

        return ParseResult(lines=lines, images=[])