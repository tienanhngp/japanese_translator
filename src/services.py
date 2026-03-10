"""
Backend services: OCR and translation.

Each service exposes a simple callable interface so the UI layer
does not depend on any specific library directly.
"""

from __future__ import annotations

import os
import multiprocessing
import tempfile
from typing import Literal, Optional

from PIL import Image
from manga_ocr import MangaOcr
from deep_translator import GoogleTranslator
from llama_cpp import Llama

from src.config import (
    SOURCE_LANG, TARGET_LANG,
    SUGOI_REPO_ID, SUGOI_FILENAME, SUGOI_GPU_LAYERS,
)

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
    """Supports Google Translate (online) and Sugoi-14B-Ultra (offline)."""

    def __init__(
        self,
        source: str = SOURCE_LANG,
        target: str = TARGET_LANG,
        backend: TranslatorBackend = "google",
    ) -> None:
        self._backend: TranslatorBackend = backend
        self._source = source
        self._target = target

        # Google – always created (lightweight)
        self._google = GoogleTranslator(source=source, target=target)

        # Sugoi – lazy-loaded on first use
        self._sugoi_llm: Optional[Llama] = None

    # ── public API ───────────────────────────────────────────────────────
    @property
    def backend(self) -> TranslatorBackend:
        return self._backend

    def set_backend(self, backend: TranslatorBackend) -> None:
        """Switch translator backend. Loads Sugoi model on first switch."""
        if backend == "sugoi" and self._sugoi_llm is None:
            self._load_sugoi()
        self._backend = backend

    def translate(self, text: str) -> str:
        """Translate *text* using the active backend."""
        if self._backend == "sugoi":
            return self._translate_sugoi(text)
        return self._google.translate(text)

    # ── Sugoi internals ──────────────────────────────────────────────────
    def _load_sugoi(self) -> None:
        """Load the Sugoi-14B-Ultra GGUF model via llama-cpp-python.

        The model is automatically downloaded from Hugging Face and
        cached locally on first use.
        """
        
        print(f"⏬ Loading Sugoi model ({SUGOI_REPO_ID}) …")
        cpu_count = multiprocessing.cpu_count()
        print(f"   GPU layers: {SUGOI_GPU_LAYERS} | CPU threads: {cpu_count}")
        self._sugoi_llm = Llama.from_pretrained(
            repo_id=SUGOI_REPO_ID,
            filename=SUGOI_FILENAME,
            n_ctx=2048,
            n_batch=512,
            n_ubatch=512,
            n_threads=cpu_count,
            n_threads_batch=cpu_count,
            n_gpu_layers=SUGOI_GPU_LAYERS,  # -1 = all layers on GPU
            use_mmap=True,
            use_mlock=False,
            offload_kqv=True,   # offload KV cache to GPU as well
            verbose=True,
        )
        print("✅ Sugoi model ready.")

    def _translate_sugoi(self, text: str) -> str:
        if self._sugoi_llm is None:
            self._load_sugoi()

        response = self._sugoi_llm.create_chat_completion(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a professional Japanese to English translator "
                        "specializing in manga and light novels. "
                        "Translate the following Japanese text to natural English. "
                        "Only output the translation, nothing else."
                    ),
                },
                {"role": "user", "content": text},
            ],
            max_tokens=256,
            temperature=0.1,
            top_p=0.9,
            top_k=40,
            repeat_penalty=1.1,
        )
        return response["choices"][0]["message"]["content"].strip()


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
