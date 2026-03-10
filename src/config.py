"""
Application-wide constants and configuration.
"""

# ── Window ────────────────────────────────────────────────────────────────
APP_TITLE = "Manga Translator"
WINDOW_SIZE = "1150x750"
MIN_WIDTH = 1150
MIN_HEIGHT = 750

# ── Appearance ────────────────────────────────────────────────────────────
APPEARANCE_MODE = "dark"
COLOR_THEME = "blue"

SNIP_BUTTON_COLOR = "#e84393"
SNIP_BUTTON_HOVER = "#d63384"
SELECTION_OUTLINE = "#00aaff"
OVERLAY_TINT = (0, 0, 0, 100)  # RGBA

FONT_BODY = ("", 16)
FONT_HEADING = ("", 14, "bold")
FONT_OVERLAY = ("Segoe UI", 16, "bold")

# ── Image Preview ────────────────────────────────────────────────────────
IMAGE_MAX_WIDTH = 620
IMAGE_MAX_HEIGHT = 600
MIN_SNIP_SIZE = 10  # pixels – ignore selections smaller than this

# ── Translation ──────────────────────────────────────────────────────────
SOURCE_LANG = "ja"
TARGET_LANG = "en"

# Translator backend: "google" or "sugoi"
DEFAULT_TRANSLATOR = "google"

# Hugging Face model ID for Sugoi / Opus-MT offline translator.
# Auto-downloaded and cached by transformers on first use.
SUGOI_MODEL_NAME = "Helsinki-NLP/opus-mt-ja-en"

# ── Files ────────────────────────────────────────────────────────────────
SUPPORTED_IMAGE_TYPES = [
    ("Image files", "*.png *.jpg *.jpeg *.bmp *.webp *.tiff"),
    ("All files", "*.*"),
]

# ── Hotkeys ──────────────────────────────────────────────────────────────
SNIP_HOTKEY_LABEL = "Ctrl+Shift+X"

# ── Status Messages ──────────────────────────────────────────────────────
STATUS_LOADING = ("Loading OCR model…", "orange")
STATUS_READY = ("✅ OCR model ready", "green")
STATUS_EXTRACTING = ("⏳ Extracting text…", "yellow")
STATUS_TRANSLATING = ("⏳ Translating…", "yellow")
STATUS_DONE = ("✅ Done", "green")
STATUS_OCR_FAIL = ("❌ OCR failed", "red")
STATUS_TRANSLATE_FAIL = ("❌ Translation failed", "red")
STATUS_MODEL_ERROR = ("❌ Model error", "red")
STATUS_SUGOI_LOADING = ("⏳ Loading Sugoi model…", "orange")
STATUS_SUGOI_READY = ("🔌 Sugoi (Offline) active", "green")

PLACEHOLDER_TEXT = (
    "No image loaded\n\n"
    "Click  ✂ Snip Screen  to capture a region\n"
    "or open / paste an image"
)

# ── Live Overlay Appearance ──────────────────────────────────────────────
LIVE_TOOLTIP_BG = "#1a1a2e"            # tooltip background
LIVE_TOOLTIP_FG = "#ffffff"            # tooltip text colour
LIVE_TOOLTIP_FONT = ("Segoe UI", 13)
LIVE_TOOLTIP_OUTLINE = "#00aaff"       # tooltip border colour
LIVE_SCROLL_SPEED = 3                  # scroll-wheel units per tick

LIVE_BUTTON_COLOR = "#6c5ce7"
LIVE_BUTTON_HOVER = "#5a4bd1"
LIVE_HOTKEY_LABEL = "Ctrl+Shift+L"

# ── Status Messages for Live Mode ────────────────────────────────────────
STATUS_LIVE_ON = ("🔍 Live Translate active", "cyan")
STATUS_LIVE_OFF = ("Live Translate ended", "white")
