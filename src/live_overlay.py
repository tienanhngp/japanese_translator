"""
LiveOverlay – fullscreen overlay for snip-and-translate-in-place.

The user stays on a frozen screenshot and can repeatedly drag-select
regions to OCR + translate.  Results appear as tooltips directly on
the overlay.  Right-click dismisses the current tooltip so the user
can select the next region.  Mouse-wheel scrolls if the captured
image is taller than the viewport.  ESC exits.
"""

from __future__ import annotations

import threading
import tkinter as tk
from typing import Callable, Optional

from PIL import Image, ImageTk, ImageGrab

from src.config import (
    SELECTION_OUTLINE,
    FONT_OVERLAY,
    MIN_SNIP_SIZE,
    LIVE_TOOLTIP_BG,
    LIVE_TOOLTIP_FG,
    LIVE_TOOLTIP_FONT,
    LIVE_TOOLTIP_OUTLINE,
    LIVE_SCROLL_SPEED,
)
from src.services import OCRService, TranslationService, save_temp_image


class LiveOverlay(tk.Toplevel):
    """Fullscreen overlay: snip regions → see translations in-place.

    Lifecycle
    ---------
    1.  Takes a full-screen screenshot.
    2.  User drags to select a text region (like normal snip).
    3.  OCR + translation runs in a thread; a tooltip appears.
    4.  Right-click clears the tooltip so the user can snip again.
    5.  ESC closes the overlay and returns to the main app.
    """

    _SNIP_COUNT: int = 0  # unique filenames for temp images

    def __init__(
        self,
        master: tk.Tk,
        ocr: OCRService,
        translator: TranslationService,
        callback: Callable[[None], None],
    ) -> None:
        super().__init__(master)
        self._ocr = ocr
        self._translator = translator
        self._callback = callback

        # Grab full screen
        self._screenshot = ImageGrab.grab(all_screens=True)
        self._img_w, self._img_h = self._screenshot.size

        # Scroll offset
        self._scroll_y = 0

        # Drag state
        self._start_x = 0
        self._start_y = 0
        self._rect_id: Optional[int] = None
        self._dragging = False

        # Translation state
        self._translating = False  # block new snips while translating

        self._configure_window()
        self._draw_background()
        self._bind_events()

    # ── Window setup ─────────────────────────────────────────────────────
    def _configure_window(self) -> None:
        self.attributes("-fullscreen", True)
        self.attributes("-topmost", True)
        self.overrideredirect(True)
        self.configure(cursor="crosshair")

    def _draw_background(self) -> None:
        self._canvas = tk.Canvas(
            self,
            highlightthickness=0,
            scrollregion=(0, 0, self._img_w, self._img_h),
        )
        self._canvas.pack(fill="both", expand=True)

        # Frozen screenshot
        self._tk_screenshot = ImageTk.PhotoImage(self._screenshot)
        self._canvas.create_image(0, 0, anchor="nw", image=self._tk_screenshot)

        # Light tint
        tint = Image.new("RGBA", self._screenshot.size, (0, 0, 0, 50))
        self._tk_tint = ImageTk.PhotoImage(tint)
        self._canvas.create_image(0, 0, anchor="nw", image=self._tk_tint)

        # Instruction banner
        self._canvas.create_text(
            self._img_w // 2, 28,
            text="Drag to select text  ·  Right-click to dismiss  ·  Scroll to pan  ·  ESC to exit",
            fill="white",
            font=FONT_OVERLAY,
        )

    def _bind_events(self) -> None:
        self._canvas.bind("<ButtonPress-1>", self._on_press)
        self._canvas.bind("<B1-Motion>", self._on_drag)
        self._canvas.bind("<ButtonRelease-1>", self._on_release)
        self._canvas.bind("<ButtonPress-3>", self._on_right_click)
        self._canvas.bind("<MouseWheel>", self._on_scroll)
        self.bind("<Escape>", lambda _: self._close())
        self.after(50, self.focus_force)

    # ── Coordinate helpers (account for scroll offset) ───────────────────
    def _canvas_x(self, event_x: int) -> int:
        return int(self._canvas.canvasx(event_x))

    def _canvas_y(self, event_y: int) -> int:
        return int(self._canvas.canvasy(event_y))

    # ── Mouse: drag-select ───────────────────────────────────────────────
    def _on_press(self, event: tk.Event) -> None:
        if self._translating:
            return
        self._start_x = self._canvas_x(event.x)
        self._start_y = self._canvas_y(event.y)
        self._dragging = True
        self._delete_rect()

    def _on_drag(self, event: tk.Event) -> None:
        if not self._dragging:
            return
        self._delete_rect()
        cx, cy = self._canvas_x(event.x), self._canvas_y(event.y)
        self._rect_id = self._canvas.create_rectangle(
            self._start_x, self._start_y, cx, cy,
            outline=SELECTION_OUTLINE,
            width=2,
        )

    def _on_release(self, event: tk.Event) -> None:
        if not self._dragging:
            return
        self._dragging = False

        cx = self._canvas_x(event.x)
        cy = self._canvas_y(event.y)
        x0, x1 = sorted((self._start_x, cx))
        y0, y1 = sorted((self._start_y, cy))

        if (x1 - x0) < MIN_SNIP_SIZE or (y1 - y0) < MIN_SNIP_SIZE:
            self._delete_rect()
            return

        # Clamp to image bounds
        x0 = max(0, x0)
        y0 = max(0, y0)
        x1 = min(self._img_w, x1)
        y1 = min(self._img_h, y1)

        # Block further snips while translating
        self._translating = True
        self.configure(cursor="watch")

        # Show a "translating…" tooltip immediately
        self._show_tooltip(x0, y0, x1, y1, "⏳ Translating…")

        # Crop and translate in background
        region = self._screenshot.crop((x0, y0, x1, y1))
        self._start_translate(region, x0, y0, x1, y1)

    # ── Mouse: right-click to dismiss tooltip ────────────────────────────
    def _on_right_click(self, _event: tk.Event) -> None:
        self._clear_tooltip()
        self._delete_rect()
        if not self._translating:
            self.configure(cursor="crosshair")

    # ── Mouse: scroll to pan ─────────────────────────────────────────────
    def _on_scroll(self, event: tk.Event) -> None:
        direction = -1 if event.delta > 0 else 1
        self._canvas.yview_scroll(direction * LIVE_SCROLL_SPEED, "units")

    # ── Translation pipeline ─────────────────────────────────────────────
    def _start_translate(
        self,
        region: Image.Image,
        x0: int, y0: int, x1: int, y1: int,
    ) -> None:
        LiveOverlay._SNIP_COUNT += 1
        name = f"_live_snip_{LiveOverlay._SNIP_COUNT}.png"

        def _worker() -> None:
            try:
                path = save_temp_image(region, name)
                jp_text = self._ocr.extract_text(path)
                if not jp_text.strip():
                    result = "(no text detected)"
                else:
                    en_text = self._translator.translate(jp_text)
                    result = f"{en_text}\n\n— {jp_text}"
            except Exception as exc:
                result = f"❌ {exc}"
            self.after(0, lambda: self._on_translated(result, x0, y0, x1, y1))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_translated(
        self, text: str,
        x0: int, y0: int, x1: int, y1: int,
    ) -> None:
        self._translating = False
        self.configure(cursor="crosshair")
        self._clear_tooltip()
        self._show_tooltip(x0, y0, x1, y1, text)

    # ── Tooltip ──────────────────────────────────────────────────────────
    def _show_tooltip(
        self,
        x0: int, y0: int, x1: int, y1: int,
        text: str,
    ) -> None:
        self._clear_tooltip()

        cx = (x0 + x1) // 2
        # Try below the selection first
        ty = y1 + 12
        anchor = "n"
        if ty + 60 > self._img_h:
            ty = y0 - 12
            anchor = "s"

        wrapped = self._wrap_text(text, max_chars=55)

        tag = "tooltip"
        self._canvas.create_text(
            cx, ty,
            text=wrapped,
            fill=LIVE_TOOLTIP_FG,
            font=LIVE_TOOLTIP_FONT,
            anchor=anchor,
            justify="center",
            tags=(tag,),
        )

        bbox = self._canvas.bbox(tag)
        if bbox:
            pad = 10
            bg = self._canvas.create_rectangle(
                bbox[0] - pad, bbox[1] - pad,
                bbox[2] + pad, bbox[3] + pad,
                fill=LIVE_TOOLTIP_BG,
                outline=LIVE_TOOLTIP_OUTLINE,
                width=1,
                tags=(tag,),
            )
            self._canvas.tag_lower(bg, tag)

    def _clear_tooltip(self) -> None:
        self._canvas.delete("tooltip")

    # ── Selection rectangle ──────────────────────────────────────────────
    def _delete_rect(self) -> None:
        if self._rect_id is not None:
            self._canvas.delete(self._rect_id)
            self._rect_id = None

    # ── Close ────────────────────────────────────────────────────────────
    def _close(self) -> None:
        self.destroy()
        self._callback(None)

    # ── Helpers ──────────────────────────────────────────────────────────
    @staticmethod
    def _wrap_text(text: str, max_chars: int = 55) -> str:
        lines: list[str] = []
        for raw_line in text.split("\n"):
            words = raw_line.split()
            if not words:
                lines.append("")
                continue
            current = ""
            for w in words:
                if current and len(current) + len(w) + 1 > max_chars:
                    lines.append(current)
                    current = w
                else:
                    current = f"{current} {w}" if current else w
            lines.append(current)
        return "\n".join(lines)
