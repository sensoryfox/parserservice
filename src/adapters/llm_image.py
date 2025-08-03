from __future__ import annotations

import base64
import json
from typing import Final

import aiohttp


class ImageDescriber:
    """
    Класс-заглушка для генерации alt-текста изображений.

    • Если указан `api_url`, выполняет реальный HTTP-запрос (POST multipart
      с файлом). Предполагается, что ответ JSON содержит поле
      `description` / `alt_text`.

    • Если URL не задан — возвращает статичный текст «Image».
    """

    _DEFAULT_ALT: Final[str] = "Image"

    def __init__(self, *, api_url: str | None, api_key: str | None = None):
        self._url = api_url
        self._api_key = api_key

    # -----------------------------------------------------------------
    async def describe(self, img_bytes: bytes) -> str:
        if not self._url:
            return self._DEFAULT_ALT

        headers: dict[str, str] = {}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        async with aiohttp.ClientSession(headers=headers) as session:
            form = aiohttp.FormData()
            # Отправляем файл как base64 — так проще для большинства серверов
            form.add_field(
                "file",
                base64.b64encode(img_bytes),
                filename="image.b64",
                content_type="application/octet-stream",
            )
            async with session.post(self._url, data=form) as resp:
                resp.raise_for_status()
                try:
                    data: dict = await resp.json()
                except aiohttp.ContentTypeError:
                    text = await resp.text()
                    raise RuntimeError(f"LLM returned non-JSON: {text}")

        return data.get("description") or data.get("alt_text") or self._DEFAULT_ALT