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
    STATUS_SUGOI_LOADING, STATUS_SUGOI_READY,
    LIVE_BUTTON_COLOR, LIVE_BUTTON_HOVER, LIVE_HOTKEY_LABEL,
    STATUS_LIVE_ON, STATUS_LIVE_OFF,
    TOOLBAR_HOTKEY_LABEL, TOOLBAR_BUTTON_COLOR, TOOLBAR_BUTTON_HOVER,
)
from src.services import OCRService, TranslationService, fit_image, save_temp_image
from src.snip_overlay import SnipOverlay
from src.live_overlay import LiveOverlay

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
        self._toolbar_only = False  # toolbar-only mode flag
        self._toolbar_window: ctk.CTkToplevel | None = None

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
        self.bind_all("<Control-Shift-l>", lambda _: self._toggle_live_mode())
        self.bind_all("<Control-Shift-L>", lambda _: self._toggle_live_mode())
        self.bind_all("<Control-Shift-t>", lambda _: self._toggle_toolbar_only())
        self.bind_all("<Control-Shift-T>", lambda _: self._toggle_toolbar_only())

    # ── Translator Backend ───────────────────────────────────────────────
    def _on_backend_changed(self, choice: str) -> None:
        """Called when the user picks a different translator from the dropdown."""
        backend = "sugoi" if "Sugoi" in choice else "google"

        if backend == "sugoi" and not self._translator.is_sugoi_loaded:
            # Load in background so the UI stays responsive
            self._backend_menu.configure(state="disabled")
            self._btn_translate.configure(state="disabled")
            self._btn_snip.configure(state="disabled")
            self._btn_open.configure(state="disabled")
            self._btn_paste.configure(state="disabled")
            self._set_status(STATUS_SUGOI_LOADING)

            def _worker() -> None:
                try:
                    self._translator.set_backend(backend)
                    self.after(0, self._on_sugoi_loaded)
                except Exception as exc:
                    msg = str(exc)
                    self.after(0, lambda: self._on_sugoi_error(msg))

            threading.Thread(target=_worker, daemon=True).start()
        else:
            self._translator.set_backend(backend)
            if backend == "sugoi":
                self._set_status(STATUS_SUGOI_READY)
            else:
                self._set_status(STATUS_READY)

    def _on_sugoi_loaded(self) -> None:
        """Re-enable UI after the Sugoi model finishes loading."""
        self._backend_menu.configure(state="normal")
        self._btn_snip.configure(state="normal")
        self._btn_open.configure(state="normal")
        self._btn_paste.configure(state="normal")
        if self._current_image_path:
            self._btn_translate.configure(state="normal")
        self._set_status(STATUS_SUGOI_READY)

    def _on_sugoi_error(self, err: str) -> None:
        """Revert to Google Translate when Sugoi fails to load."""
        self._backend_var.set("Google Translate")
        self._translator.set_backend("google")
        self._backend_menu.configure(state="normal")
        self._btn_snip.configure(state="normal")
        self._btn_open.configure(state="normal")
        self._btn_paste.configure(state="normal")
        self._set_status(STATUS_READY)
        messagebox.showerror("Sugoi Error", err)

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

        self._btn_live = ctk.CTkButton(
            toolbar,
            text=f"🔍 Live ({LIVE_HOTKEY_LABEL})",
            command=self._toggle_live_mode,
            width=170,
            fg_color=LIVE_BUTTON_COLOR,
            hover_color=LIVE_BUTTON_HOVER,
        )
        self._btn_live.pack(side="left", padx=5, pady=5)

        self._btn_toolbar_only = ctk.CTkButton(
            toolbar,
            text=f"🔲 Toolbar ({TOOLBAR_HOTKEY_LABEL})",
            command=self._toggle_toolbar_only,
            width=170,
            fg_color=TOOLBAR_BUTTON_COLOR,
            hover_color=TOOLBAR_BUTTON_HOVER,
        )
        self._btn_toolbar_only.pack(side="left", padx=5, pady=5)

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
        # Also update toolbar status if it exists
        if self._toolbar_only and self._toolbar_window is not None:
            try:
                self._tb_status.configure(text=status[0], text_color=status[1])
            except Exception:
                pass

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
        if self._toolbar_only:
            self._tb_snip_screen()
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
    #  Live Translate Mode
    # ══════════════════════════════════════════════════════════════════════
    def _toggle_live_mode(self) -> None:
        """Activate live hover-to-translate overlay."""
        if not self._ocr.is_ready:
            messagebox.showinfo("Not Ready", "OCR model is still loading, please wait.")
            return
        if self._toolbar_only:
            self._tb_toggle_live()
            return
        self.withdraw()
        self.update()
        self.after(200, self._show_live_overlay)

    def _show_live_overlay(self) -> None:
        LiveOverlay(self, self._ocr, self._translator, self._on_live_done)

    def _on_live_done(self, _: None) -> None:
        if self._toolbar_only and self._toolbar_window is not None:
            self._toolbar_window.deiconify()
            self._toolbar_window.lift()
            self._tb_status.configure(
                text=STATUS_LIVE_OFF[0], text_color=STATUS_LIVE_OFF[1]
            )
        else:
            self.deiconify()
            self.lift()
            self._set_status(STATUS_LIVE_OFF)

    # ══════════════════════════════════════════════════════════════════════
    #  Toolbar-Only Mode
    # ══════════════════════════════════════════════════════════════════════
    def _toggle_toolbar_only(self) -> None:
        """Switch between full window and compact floating toolbar."""
        if self._toolbar_only:
            self._close_toolbar_window()
        else:
            self._open_toolbar_window()

    def _open_toolbar_window(self) -> None:
        """Hide the main window and show a compact floating toolbar."""
        self._toolbar_only = True
        self.withdraw()

        win = ctk.CTkToplevel(self)
        self._toolbar_window = win
        win.title("Manga Translator – Toolbar")
        win.attributes("-topmost", True)
        win.resizable(False, False)
        win.protocol("WM_DELETE_WINDOW", self._close_toolbar_window)

        frame = ctk.CTkFrame(win, corner_radius=8)
        frame.pack(fill="both", expand=True, padx=6, pady=6)

        # ── Snip button ──────────────────────────────────────────────────
        ctk.CTkButton(
            frame,
            text=f"✂ Snip ({SNIP_HOTKEY_LABEL})",
            command=self._tb_snip_screen,
            width=150,
            fg_color=SNIP_BUTTON_COLOR,
            hover_color=SNIP_BUTTON_HOVER,
        ).pack(side="left", padx=4, pady=6)

        # ── Live button ──────────────────────────────────────────────────
        ctk.CTkButton(
            frame,
            text=f"🔍 Live ({LIVE_HOTKEY_LABEL})",
            command=self._tb_toggle_live,
            width=150,
            fg_color=LIVE_BUTTON_COLOR,
            hover_color=LIVE_BUTTON_HOVER,
        ).pack(side="left", padx=4, pady=6)

        # ── Backend selector ─────────────────────────────────────────────
        self._tb_backend_var = ctk.StringVar(value=self._backend_var.get())
        self._tb_backend_menu = ctk.CTkOptionMenu(
            frame,
            values=["Google Translate", "Sugoi (Offline)"],
            variable=self._tb_backend_var,
            command=self._on_backend_changed,
            width=150,
        )
        self._tb_backend_menu.pack(side="left", padx=4, pady=6)

        # ── Status label ─────────────────────────────────────────────────
        current_status = self._status.cget("text")
        current_color = self._status.cget("text_color")
        self._tb_status = ctk.CTkLabel(
            frame, text=current_status, text_color=current_color,
        )
        self._tb_status.pack(side="left", padx=8, pady=6)

        # ── Expand (back to full window) ─────────────────────────────────
        ctk.CTkButton(
            frame,
            text="⬜ Expand",
            command=self._close_toolbar_window,
            width=80,
            fg_color="gray40",
            hover_color="gray50",
        ).pack(side="right", padx=4, pady=6)

        # Position at top-center of screen
        win.update_idletasks()
        sw = win.winfo_screenwidth()
        ww = win.winfo_reqwidth()
        win.geometry(f"+{(sw - ww) // 2}+0")

        # Bind hotkeys on the toolbar window too
        win.bind_all("<Control-Shift-x>", lambda _: self._tb_snip_screen())
        win.bind_all("<Control-Shift-X>", lambda _: self._tb_snip_screen())
        win.bind_all("<Control-Shift-l>", lambda _: self._tb_toggle_live())
        win.bind_all("<Control-Shift-L>", lambda _: self._tb_toggle_live())
        win.bind_all("<Control-Shift-t>", lambda _: self._close_toolbar_window())
        win.bind_all("<Control-Shift-T>", lambda _: self._close_toolbar_window())

    def _close_toolbar_window(self) -> None:
        """Close the floating toolbar and restore the main window."""
        self._toolbar_only = False
        if self._toolbar_window is not None:
            self._toolbar_window.destroy()
            self._toolbar_window = None
        self.deiconify()
        self.lift()
        self._bind_hotkeys()  # rebind hotkeys to the main window

    def _tb_snip_screen(self) -> None:
        """Snip screen from the toolbar-only mode."""
        if not self._ocr.is_ready:
            from tkinter import messagebox
            messagebox.showinfo("Not Ready", "OCR model is still loading, please wait.")
            return
        if self._toolbar_window:
            self._toolbar_window.withdraw()
        self.update()
        self.after(200, self._show_snip_overlay_toolbar)

    def _show_snip_overlay_toolbar(self) -> None:
        SnipOverlay(self, self._on_snip_done_toolbar)

    def _on_snip_done_toolbar(self, region: Image.Image | None) -> None:
        """Handle snip result in toolbar mode — show result then restore toolbar."""
        if self._toolbar_window:
            self._toolbar_window.deiconify()
            self._toolbar_window.lift()
        if region is None:
            return
        path = save_temp_image(region, "_manga_snip.png")
        # In toolbar mode, show the full window briefly for results
        self._display_image(region, path)
        self.deiconify()
        self.lift()
        self._extract_and_translate()

    def _tb_toggle_live(self) -> None:
        """Start live overlay from toolbar mode."""
        if not self._ocr.is_ready:
            from tkinter import messagebox
            messagebox.showinfo("Not Ready", "OCR model is still loading, please wait.")
            return
        if self._toolbar_window:
            self._toolbar_window.withdraw()
        self.update()
        self.after(200, self._show_live_overlay)

    def _tb_set_status(self, status: tuple[str, str]) -> None:
        """Update status on both the main status label and toolbar status."""
        self._status.configure(text=status[0], text_color=status[1])
        if self._toolbar_window is not None and self._tb_status is not None:
            self._tb_status.configure(text=status[0], text_color=status[1])

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
    import sys
    app = MangaTranslateApp()
    if "--toolbar" in sys.argv:
        app.after(500, app._toggle_toolbar_only)
    app.mainloop()
