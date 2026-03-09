"""
Backend services: OCR and translation.

Each service exposes a simple callable interface so the UI layer
does not depend on any specific library directly.
"""

from __future__ import annotations

import os
import tempfile
from typing import Literal, Optional

from PIL import Image
from manga_ocr import MangaOcr
from deep_translator import GoogleTranslator
from transformers import MarianMTModel, MarianTokenizer

from src.config import SOURCE_LANG, TARGET_LANG, SUGOI_MODEL_NAME

TranslatorBackend = Literal["google", "sugoi"]


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
    """Supports Google Translate (online) and Sugoi/Opus-MT (offline)."""

    def __init__(
        self,
        source: str = SOURCE_LANG,
        target: str = TARGET_LANG,
        backend: TranslatorBackend = "google",
        sugoi_model_name: str = SUGOI_MODEL_NAME,
    ) -> None:
        self._backend: TranslatorBackend = backend
        self._source = source
        self._target = target
        self._sugoi_model_name = sugoi_model_name

        # Google – always created (lightweight)
        self._google = GoogleTranslator(source=source, target=target)

        # Sugoi – lazy-loaded on first use
        self._sugoi_model: Optional[MarianMTModel] = None
        self._sugoi_tokenizer: Optional[MarianTokenizer] = None

    # ── public API ───────────────────────────────────────────────────────
    @property
    def backend(self) -> TranslatorBackend:
        return self._backend

    def set_backend(self, backend: TranslatorBackend) -> None:
        """Switch translator backend. Loads Sugoi model on first switch."""
        if backend == "sugoi" and self._sugoi_model is None:
            self._load_sugoi()
        self._backend = backend

    def translate(self, text: str) -> str:
        """Translate *text* using the active backend."""
        if self._backend == "sugoi":
            return self._translate_sugoi(text)
        return self._google.translate(text)

    # ── Sugoi internals ──────────────────────────────────────────────────
    def _load_sugoi(self) -> None:
        """Load the Marian MT model from Hugging Face.

        The model is automatically downloaded and cached by the
        transformers library on first use.
        """
        print(f"⏬ Loading Sugoi model ({self._sugoi_model_name}) …")
        self._sugoi_tokenizer = MarianTokenizer.from_pretrained(self._sugoi_model_name)
        self._sugoi_model = MarianMTModel.from_pretrained(self._sugoi_model_name)
        print("✅ Sugoi model ready.")

    def _translate_sugoi(self, text: str) -> str:
        if self._sugoi_model is None or self._sugoi_tokenizer is None:
            self._load_sugoi()
        inputs = self._sugoi_tokenizer(text, return_tensors="pt", padding=True)
        translated = self._sugoi_model.generate(**inputs)
        return self._sugoi_tokenizer.decode(translated[0], skip_special_tokens=True)


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
