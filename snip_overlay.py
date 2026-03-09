"""
SnipOverlay – fullscreen transparent overlay for drag-selecting
a screen region, similar to Windows Snip & Sketch.
"""

from __future__ import annotations

import tkinter as tk
from typing import Callable, Optional

from PIL import Image, ImageTk, ImageGrab

from config import (
    MIN_SNIP_SIZE,
    OVERLAY_TINT,
    SELECTION_OUTLINE,
    FONT_OVERLAY,
)


class SnipOverlay(tk.Toplevel):
    """Fullscreen overlay that lets the user drag-select a screen region.

    Parameters
    ----------
    master : tk.Tk
        Parent window (will be hidden while the overlay is active).
    callback : callable
        Called with a ``PIL.Image`` of the selected region, or ``None``
        if the user pressed Escape.
    """

    def __init__(
        self,
        master: tk.Tk,
        callback: Callable[[Optional[Image.Image]], None],
    ) -> None:
        super().__init__(master)
        self._callback = callback

        # Grab the screen BEFORE the overlay is visible
        self._screenshot = ImageGrab.grab(all_screens=True)

        self._configure_window()
        self._draw_background()
        self._bind_events()

        # Drag state
        self._start_x = 0
        self._start_y = 0
        self._rect_id: Optional[int] = None

    # ── Setup ────────────────────────────────────────────────────────────
    def _configure_window(self) -> None:
        self.attributes("-fullscreen", True)
        self.attributes("-topmost", True)
        self.overrideredirect(True)
        self.configure(cursor="crosshair")

    def _draw_background(self) -> None:
        self._canvas = tk.Canvas(self, highlightthickness=0)
        self._canvas.pack(fill="both", expand=True)

        # Frozen screenshot
        self._tk_screenshot = ImageTk.PhotoImage(self._screenshot)
        self._canvas.create_image(0, 0, anchor="nw", image=self._tk_screenshot)

        # Dark tint
        tint = Image.new("RGBA", self._screenshot.size, OVERLAY_TINT)
        self._tk_tint = ImageTk.PhotoImage(tint)
        self._canvas.create_image(0, 0, anchor="nw", image=self._tk_tint)

        # Instruction label
        self._canvas.create_text(
            self._screenshot.width // 2,
            30,
            text="Drag to select region  ·  ESC to cancel",
            fill="white",
            font=FONT_OVERLAY,
        )

    def _bind_events(self) -> None:
        self._canvas.bind("<ButtonPress-1>", self._on_press)
        self._canvas.bind("<B1-Motion>", self._on_drag)
        self._canvas.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<Escape>", lambda _: self._cancel())

    # ── Mouse Handlers ───────────────────────────────────────────────────
    def _on_press(self, event: tk.Event) -> None:
        self._start_x, self._start_y = event.x, event.y
        self._delete_rect()

    def _on_drag(self, event: tk.Event) -> None:
        self._delete_rect()
        self._rect_id = self._canvas.create_rectangle(
            self._start_x,
            self._start_y,
            event.x,
            event.y,
            outline=SELECTION_OUTLINE,
            width=2,
        )

    def _on_release(self, event: tk.Event) -> None:
        x0 = min(self._start_x, event.x)
        y0 = min(self._start_y, event.y)
        x1 = max(self._start_x, event.x)
        y1 = max(self._start_y, event.y)

        if (x1 - x0) < MIN_SNIP_SIZE or (y1 - y0) < MIN_SNIP_SIZE:
            self._cancel()
            return

        region = self._screenshot.crop((x0, y0, x1, y1))
        self.destroy()
        self._callback(region)

    # ── Helpers ──────────────────────────────────────────────────────────
    def _delete_rect(self) -> None:
        if self._rect_id is not None:
            self._canvas.delete(self._rect_id)
            self._rect_id = None

    def _cancel(self) -> None:
        self.destroy()
        self._callback(None)
