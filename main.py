"""
Manga Translate App – Real-time screen snipping + OCR + Translation.

Entry point.  Run with:  python app.py
"""

from __future__ import annotations

import os
import threading
import customtkinter as ctk
from tkinter import filedialog, messagebox
from PIL import Image, ImageGrab

from src.platform_utils import enable_dpi_awareness
from src.config import (
    APP_TITLE, WINDOW_SIZE, MIN_WIDTH, MIN_HEIGHT,
    APPEARANCE_MODE, COLOR_THEME,
    SNIP_BUTTON_COLOR, SNIP_BUTTON_HOVER, SNIP_HOTKEY_LABEL,
    FONT_BODY, FONT_HEADING,
    IMAGE_MAX_WIDTH, IMAGE_MAX_HEIGHT,
    SUPPORTED_IMAGE_TYPES, PLACEHOLDER_TEXT,
    STATUS_LOADING, STATUS_READY, STATUS_EXTRACTING,
    STATUS_TRANSLATING, STATUS_DONE,
    STATUS_OCR_FAIL, STATUS_TRANSLATE_FAIL, STATUS_MODEL_ERROR,
    DEFAULT_TRANSLATOR,
)
from src.services import OCRService, TranslationService, fit_image, save_temp_image
from src.snip_overlay import SnipOverlay

# Must be called before any Tk window is created
enable_dpi_awareness()


# ═══════════════════════════════════════════════════════════════════════════
#  Main Application
# ═══════════════════════════════════════════════════════════════════════════
class MangaTranslateApp(ctk.CTk):
    """Top-level application window."""

    def __init__(self) -> None:
        super().__init__()

        # Window setup
        self.title(APP_TITLE)
        self.geometry(WINDOW_SIZE)
        self.minsize(MIN_WIDTH, MIN_HEIGHT)
        ctk.set_appearance_mode(APPEARANCE_MODE)
        ctk.set_default_color_theme(COLOR_THEME)

        # Services
        self._ocr = OCRService()
        self._translator = TranslationService(backend=DEFAULT_TRANSLATOR)

        # State
        self._current_image_path: str | None = None
        self._photo_image = None  # prevent GC of CTkImage

        # Build & boot
        self._build_toolbar()
        self._build_content()
        self._build_bottom_bar()
        self._bind_hotkeys()
        self._load_ocr_model()

    # ── Hotkeys ──────────────────────────────────────────────────────────
    def _bind_hotkeys(self) -> None:
        self.bind_all("<Control-Shift-x>", lambda _: self._snip_screen())
        self.bind_all("<Control-Shift-X>", lambda _: self._snip_screen())

    # ── Translator Backend ───────────────────────────────────────────────
    def _on_backend_changed(self, choice: str) -> None:
        """Called when the user picks a different translator from the dropdown."""
        backend = "sugoi" if "Sugoi" in choice else "google"
        try:
            self._translator.set_backend(backend)
            label = "🔌 Sugoi (Offline)" if backend == "sugoi" else "🌐 Google Translate"
            self._set_status((f"{label} active", "green"))
        except Exception as exc:
            # Revert dropdown on failure
            self._backend_var.set("Google Translate")
            self._translator.set_backend("google")
            messagebox.showerror("Sugoi Error", str(exc))

    # ══════════════════════════════════════════════════════════════════════
    #  UI Construction
    # ══════════════════════════════════════════════════════════════════════
    def _build_toolbar(self) -> None:
        toolbar = ctk.CTkFrame(self, corner_radius=0)
        toolbar.pack(fill="x", padx=10, pady=(10, 5))

        self._btn_snip = ctk.CTkButton(
            toolbar,
            text=f"✂ Snip Screen ({SNIP_HOTKEY_LABEL})",
            command=self._snip_screen,
            width=220,
            fg_color=SNIP_BUTTON_COLOR,
            hover_color=SNIP_BUTTON_HOVER,
        )
        self._btn_snip.pack(side="left", padx=5, pady=5)

        self._btn_open = ctk.CTkButton(
            toolbar, text="📂 Open Image", command=self._open_image, width=130,
        )
        self._btn_open.pack(side="left", padx=5, pady=5)

        self._btn_paste = ctk.CTkButton(
            toolbar, text="📋 Paste", command=self._paste_image, width=100,
        )
        self._btn_paste.pack(side="left", padx=5, pady=5)

        self._btn_translate = ctk.CTkButton(
            toolbar, text="🔍 Extract & Translate",
            command=self._extract_and_translate, width=180, state="disabled",
        )
        self._btn_translate.pack(side="left", padx=5, pady=5)

        self._btn_clear = ctk.CTkButton(
            toolbar, text="🗑 Clear", command=self._clear, width=80,
        )
        self._btn_clear.pack(side="left", padx=5, pady=5)

        # ── Translator backend selector ──────────────────────────────────
        self._backend_var = ctk.StringVar(
            value="Google Translate" if DEFAULT_TRANSLATOR == "google" else "Sugoi (Offline)"
        )
        self._backend_menu = ctk.CTkOptionMenu(
            toolbar,
            values=["Google Translate", "Sugoi (Offline)"],
            variable=self._backend_var,
            command=self._on_backend_changed,
            width=160,
        )
        self._backend_menu.pack(side="left", padx=10, pady=5)

        self._status = ctk.CTkLabel(toolbar, text=STATUS_LOADING[0], text_color=STATUS_LOADING[1])
        self._status.pack(side="right", padx=10, pady=5)

    def _build_content(self) -> None:
        content = ctk.CTkFrame(self)
        content.pack(fill="both", expand=True, padx=10, pady=5)
        content.columnconfigure(0, weight=3)
        content.columnconfigure(1, weight=2)
        content.rowconfigure(0, weight=1)

        # ── Image panel ──────────────────────────────────────────────────
        img_frame = ctk.CTkFrame(content)
        img_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))

        self._image_label = ctk.CTkLabel(img_frame, text=PLACEHOLDER_TEXT)
        self._image_label.pack(fill="both", expand=True, padx=5, pady=5)

        # ── Text panel ───────────────────────────────────────────────────
        text_frame = ctk.CTkFrame(content)
        text_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0))

        ctk.CTkLabel(text_frame, text="Extracted Japanese Text", font=FONT_HEADING).pack(pady=(8, 2))
        self._ocr_text = ctk.CTkTextbox(text_frame, wrap="word", font=FONT_BODY)
        self._ocr_text.pack(fill="both", expand=True, padx=8, pady=(0, 5))

        ctk.CTkLabel(text_frame, text="English Translation", font=FONT_HEADING).pack(pady=(8, 2))
        self._trans_text = ctk.CTkTextbox(text_frame, wrap="word", font=FONT_BODY)
        self._trans_text.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    def _build_bottom_bar(self) -> None:
        bar = ctk.CTkFrame(self, corner_radius=0)
        bar.pack(fill="x", padx=10, pady=(5, 10))

        ctk.CTkLabel(bar, text="Manual input:").pack(side="left", padx=(5, 2), pady=5)

        self._manual_entry = ctk.CTkEntry(
            bar, placeholder_text="Type Japanese text here…", width=400,
        )
        self._manual_entry.pack(side="left", padx=5, pady=5, fill="x", expand=True)
        self._manual_entry.bind("<Return>", lambda _: self._translate_manual())

        ctk.CTkButton(
            bar, text="Translate", command=self._translate_manual, width=100,
        ).pack(side="left", padx=5, pady=5)

    # ══════════════════════════════════════════════════════════════════════
    #  Status helpers
    # ══════════════════════════════════════════════════════════════════════
    def _set_status(self, status: tuple[str, str]) -> None:
        """Update the status label.  *status* is a ``(text, color)`` tuple."""
        self._status.configure(text=status[0], text_color=status[1])

    # ══════════════════════════════════════════════════════════════════════
    #  OCR Model Loading
    # ══════════════════════════════════════════════════════════════════════
    def _load_ocr_model(self) -> None:
        def _worker() -> None:
            try:
                self._ocr.load_model()
                self.after(0, self._on_model_loaded)
            except Exception as exc:
                msg = str(exc)
                self.after(0, lambda: self._on_model_error(msg))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_model_loaded(self) -> None:
        self._set_status(STATUS_READY)
        if self._current_image_path:
            self._btn_translate.configure(state="normal")

    def _on_model_error(self, err: str) -> None:
        self._set_status(STATUS_MODEL_ERROR)
        messagebox.showerror("OCR Model Error", f"Failed to load manga-ocr:\n{err}")

    # ══════════════════════════════════════════════════════════════════════
    #  Screen Snipping
    # ══════════════════════════════════════════════════════════════════════
    def _snip_screen(self) -> None:
        if not self._ocr.is_ready:
            messagebox.showinfo("Not Ready", "OCR model is still loading, please wait.")
            return
        self.withdraw()
        self.update()
        self.after(200, self._show_snip_overlay)

    def _show_snip_overlay(self) -> None:
        SnipOverlay(self, self._on_snip_done)

    def _on_snip_done(self, region: Image.Image | None) -> None:
        self.deiconify()
        self.lift()
        if region is None:
            return
        path = save_temp_image(region, "_manga_snip.png")
        self._display_image(region, path)
        self._extract_and_translate()

    # ══════════════════════════════════════════════════════════════════════
    #  Image Loading
    # ══════════════════════════════════════════════════════════════════════
    def _open_image(self) -> None:
        path = filedialog.askopenfilename(filetypes=SUPPORTED_IMAGE_TYPES)
        if path:
            try:
                self._display_image(Image.open(path), path)
            except Exception as exc:
                messagebox.showerror("Image Error", f"Cannot open image:\n{exc}")

    def _paste_image(self) -> None:
        try:
            img = ImageGrab.grabclipboard()
            if img is None:
                messagebox.showinfo("Paste", "No image found in clipboard.")
                return
            path = save_temp_image(img, "_manga_paste.png")
            self._display_image(img, path)
        except Exception as exc:
            messagebox.showerror("Paste Error", str(exc))

    def _display_image(self, img: Image.Image, path: str) -> None:
        """Show *img* in the preview panel and store *path* for OCR."""
        self._current_image_path = path
        preview = fit_image(img, IMAGE_MAX_WIDTH, IMAGE_MAX_HEIGHT)
        self._photo_image = ctk.CTkImage(
            light_image=preview, dark_image=preview, size=preview.size,
        )
        self._image_label.configure(image=self._photo_image, text="")
        if self._ocr.is_ready:
            self._btn_translate.configure(state="normal")
        self._set_status((f"📷 {os.path.basename(path)}", "white"))

    # ══════════════════════════════════════════════════════════════════════
    #  OCR → Translation Pipeline
    # ══════════════════════════════════════════════════════════════════════
    def _extract_and_translate(self) -> None:
        if not self._current_image_path or not self._ocr.is_ready:
            return
        self._btn_translate.configure(state="disabled")
        self._set_status(STATUS_EXTRACTING)
        path = self._current_image_path

        def _worker() -> None:
            try:
                text = self._ocr.extract_text(path)
                self.after(0, lambda: self._on_ocr_success(text))
            except Exception as exc:
                msg = str(exc)
                self.after(0, lambda: self._on_ocr_error(msg))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_ocr_success(self, japanese: str) -> None:
        self._set_textbox(self._ocr_text, japanese)
        self._set_status(STATUS_TRANSLATING)
        self._run_translation(japanese)

    def _on_ocr_error(self, err: str) -> None:
        self._btn_translate.configure(state="normal")
        self._set_status(STATUS_OCR_FAIL)
        messagebox.showerror("OCR Error", err)

    def _run_translation(self, text: str) -> None:
        def _worker() -> None:
            try:
                result = self._translator.translate(text)
                self.after(0, lambda: self._on_translate_success(result))
            except Exception as exc:
                msg = str(exc)
                self.after(0, lambda: self._on_translate_error(msg))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_translate_success(self, english: str) -> None:
        self._set_textbox(self._trans_text, english)
        self._btn_translate.configure(state="normal")
        self._set_status(STATUS_DONE)

    def _on_translate_error(self, err: str) -> None:
        self._btn_translate.configure(state="normal")
        self._set_status(STATUS_TRANSLATE_FAIL)
        messagebox.showerror("Translation Error", err)

    # ══════════════════════════════════════════════════════════════════════
    #  Manual Input
    # ══════════════════════════════════════════════════════════════════════
    def _translate_manual(self) -> None:
        text = self._manual_entry.get().strip()
        if not text:
            return
        self._set_textbox(self._ocr_text, text)
        self._set_status(STATUS_TRANSLATING)
        self._run_translation(text)

    # ══════════════════════════════════════════════════════════════════════
    #  Clear
    # ══════════════════════════════════════════════════════════════════════
    def _clear(self) -> None:
        self._current_image_path = None
        self._photo_image = None
        self._image_label.configure(image="", text=PLACEHOLDER_TEXT)
        self._set_textbox(self._ocr_text, "")
        self._set_textbox(self._trans_text, "")
        self._manual_entry.delete(0, "end")
        self._btn_translate.configure(state="disabled")
        self._set_status(STATUS_READY if self._ocr.is_ready else STATUS_LOADING)

    # ══════════════════════════════════════════════════════════════════════
    #  Utilities
    # ══════════════════════════════════════════════════════════════════════
    @staticmethod
    def _set_textbox(textbox: ctk.CTkTextbox, content: str) -> None:
        textbox.delete("1.0", "end")
        if content:
            textbox.insert("1.0", content)


# ══════════════════════════════════════════════════════════════════════════
#  Entry Point
# ══════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    app = MangaTranslateApp()
    app.mainloop()
