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

# Sugoi-14B-Ultra GGUF model (auto-downloaded from Hugging Face on first use)
SUGOI_REPO_ID = "sugoitoolkit/Sugoi-14B-Ultra-GGUF"
SUGOI_FILENAME = "Sugoi-14B-Ultra-Q4_K_M.gguf"

# GPU offload layers:
#   -1 = all layers on GPU  (fastest, requires enough VRAM)
#    0 = CPU only           (slowest, no GPU needed)
#   N  = partial offload    (tune if you get out-of-memory errors)
# Recommended: start with -1, lower if you get CUDA out-of-memory errors.
SUGOI_GPU_LAYERS = 20

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

PLACEHOLDER_TEXT = (
    "No image loaded\n\n"
    "Click  ✂ Snip Screen  to capture a region\n"
    "or open / paste an image"
)
