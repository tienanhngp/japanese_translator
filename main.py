"""
Manga Translate App – Real-time screen snipping + OCR + Translation.

Entry point.  Run with:  python main.py [--toolbar]
"""

import sys
from src.platform_utils import enable_dpi_awareness
from src.app import MangaTranslateApp

# Must be called before any Tk window is created
enable_dpi_awareness()


def main() -> None:
    app = MangaTranslateApp()
    if "--toolbar" in sys.argv:
        app.after(500, app._toggle_toolbar_only)
    app.mainloop()


if __name__ == "__main__":
    main()

