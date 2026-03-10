# Manga Translator

A desktop app with a built-in **screen snipping tool** (like Snip & Sketch) that captures Japanese text from manga, runs OCR with **manga-ocr**, and translates it to English in real time.

## Features

- **✂ Screen Snip** – Select any region on your screen to instantly OCR & translate (like Snip & Sketch)
- **🔍 Live Translate** – Fullscreen overlay where you can repeatedly drag-select regions and see translations as tooltips directly on screen — no window switching needed
- **🔲 Toolbar-Only Mode** – Collapse the app into a compact always-on-top floating toolbar for quick access to Snip and Live modes without the full window getting in the way
- **Hotkey support** – Trigger snip, live translate, or toolbar mode from anywhere
- **OCR extraction** – Uses [manga-ocr](https://github.com/kha-white/manga-ocr) to read Japanese text from manga panels
- **Dual translation backends** – Google Translate (online) or Sugoi / Opus-MT (offline)
- **Image loading** – Open images from file or paste from clipboard
- **Manual input** – Type any Japanese text and get an instant translation
- **Modern UI** – Dark-themed GUI built with [customtkinter](https://github.com/TomSchimansky/CustomTkinter)

## Requirements

- Python 3.9+
- PyTorch (installed automatically with manga-ocr)

## Installation

```bash
# Create and activate a virtual environment (recommended)
python -m venv venv
venv\Scripts\activate       # Windows
# source venv/bin/activate  # macOS / Linux

# Install dependencies
pip install -r requirements.txt
```

> **Note:** The first run will download the manga-ocr model (~400 MB). This only happens once.

## Usage

```bash
python main.py
```

### Launch in Toolbar-Only Mode

Start the app directly as a compact floating toolbar:

```bash
python main.py --toolbar
```

### Workflow — Screen Snip

1. Click **✂ Snip Screen** or press **Ctrl+Shift+X**
2. The app hides and a fullscreen overlay appears with a crosshair cursor
3. **Drag to select** the region containing Japanese text
4. The app automatically runs OCR and shows the translation — no extra clicks needed
5. Press **ESC** to cancel the snip

### Workflow — Live Translate

1. Click **🔍 Live** or press **Ctrl+Shift+L**
2. A fullscreen overlay captures your screen as a frozen snapshot
3. **Drag to select** any text region — a tooltip with the translation appears in-place
4. **Right-click** to dismiss the tooltip, then select another region
5. **Scroll** to pan if the image is taller than your screen
6. Press **ESC** to exit and return to the app

### Workflow — Toolbar-Only Mode

1. Click **🔲 Toolbar** or press **Ctrl+Shift+T**
2. The full window collapses into a small always-on-top floating toolbar
3. Use the toolbar's **✂ Snip** or **🔍 Live** buttons (or hotkeys) to translate
4. When live overlay closes, you return to the toolbar — not the full window
5. Click **⬜ Expand** or press **Ctrl+Shift+T** again to restore the full window

> **Tip:** Toolbar mode is ideal for reading manga — keep the small bar on screen and press **Ctrl+Shift+L** whenever you need a translation.

### Other Options

- **📂 Open Image** – Load a manga panel from a file
- **📋 Paste** – Paste an image from the clipboard
- **🔍 Extract & Translate** – Manually trigger OCR on the loaded image
- **🗑 Clear** – Reset the current image and text
- **Backend selector** – Switch between Google Translate and Sugoi (Offline)
- **Manual input** – Type Japanese text in the bottom bar and press **Enter**

## Screenshots

### Full Window
<img width="1280" height="691" alt="App_screen_shot" src="https://github.com/user-attachments/assets/9d37bec1-e2e8-45a6-8b40-c81b580f0620" />


### Toolbar-Only Mode

<img width="712" height="166" alt="tool_bar_screenshot" src="https://github.com/user-attachments/assets/ff20114d-1208-4e99-98bb-dd93cddc68ec" />


## Keyboard Shortcuts

| Shortcut         | Action                                  |
|------------------|-----------------------------------------|
| `Ctrl+Shift+X`   | Snip a screen region                    |
| `Ctrl+Shift+L`   | Toggle Live Translate overlay           |
| `Ctrl+Shift+T`   | Toggle Toolbar-Only mode                |
| `ESC`            | Cancel snip / exit live overlay         |
| `Enter`          | Translate manual input                  |
| Right-click      | Dismiss tooltip (in Live Translate)     |
| Scroll wheel     | Pan the image (in Live Translate)       |
