"""
Backend services: OCR and translation.

Each service exposes a simple callable interface so the UI layer
does not depend on any specific library directly.
"""

from __future__ import annotations

import os
import tempfile
from typing import Optional

from PIL import Image
from manga_ocr import MangaOcr
from deep_translator import GoogleTranslator

from src.config import SOURCE_LANG, TARGET_LANG


# ── OCR Service ──────────────────────────────────────────────────────────
class OCRService:
    """Wrapper around manga-ocr."""

    def __init__(self) -> None:
        self._model: Optional[MangaOcr] = None

    @property
    def is_ready(self) -> bool:
        return self._model is not None

    def load_model(self) -> None:
        """Blocking call – run in a background thread."""
        self._model = MangaOcr()

    def extract_text(self, image_path: str) -> str:
        """Run OCR on an image file and return extracted Japanese text."""
        if self._model is None:
            raise RuntimeError("OCR model is not loaded yet.")
        return self._model(image_path)


# ── Translation Service ─────────────────────────────────────────────────
class TranslationService:
    """Wrapper around deep-translator / Google Translate."""

    def __init__(
        self,
        source: str = SOURCE_LANG,
        target: str = TARGET_LANG,
    ) -> None:
        self._translator = GoogleTranslator(source=source, target=target)

    def translate(self, text: str) -> str:
        """Translate *text* and return the result."""
        return self._translator.translate(text)


# ── Image helpers ────────────────────────────────────────────────────────
def fit_image(img: Image.Image, max_w: int, max_h: int) -> Image.Image:
    """Return a copy of *img* scaled to fit within *max_w* × *max_h*."""
    w, h = img.size
    ratio = min(max_w / w, max_h / h, 1.0)
    new_size = (int(w * ratio), int(h * ratio))
    return img.resize(new_size, Image.LANCZOS)


def save_temp_image(img: Image.Image, name: str = "_manga_tmp.png") -> str:
    """Save a PIL image to a temp file and return the path."""
    path = os.path.join(tempfile.gettempdir(), name)
    img.save(path)
    return path
