"""
Platform helpers (DPI awareness, etc.).
"""

import ctypes
import sys


def enable_dpi_awareness() -> None:
    """Make the process DPI-aware on Windows so Tkinter coordinates
    match actual screen pixels.  Safe no-op on other platforms."""
    if sys.platform != "win32":
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # Per-Monitor V2
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()   # Fallback
        except Exception:
            pass
