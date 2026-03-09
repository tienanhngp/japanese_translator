# Manga Translator

A desktop app with a built-in **screen snipping tool** (like Snip & Sketch) that captures Japanese text from manga, runs OCR with **manga-ocr**, and translates it to English in real time.

## Features

- **✂ Screen Snip** – Select any region on your screen to instantly OCR & translate (like Snip & Sketch)
- **Hotkey support** – Press **Ctrl+Shift+X** to snip from anywhere
- **OCR extraction** – Uses [manga-ocr](https://github.com/kha-white/manga-ocr) to read Japanese text from manga panels
- **Translation** – Translates extracted Japanese text to English via Google Translate
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
python app.py
```

### Workflow

1. **Snip Screen** – Click **✂ Snip Screen** or press **Ctrl+Shift+X**
2. The app hides and a fullscreen overlay appears with a crosshair cursor
3. **Drag to select** the region containing Japanese text
4. The app automatically runs OCR and shows the translation — no extra clicks needed
5. Press **ESC** to cancel the snip

### Other options

- **Open Image** – Load a manga panel from a file
- **Paste** – Paste an image from the clipboard
- **Extract & Translate** – Manually trigger OCR on the loaded image
- **Manual input** – Type Japanese text in the bottom bar and press **Enter**

## Screenshot

```
<img width="2556" height="1381" alt="image" src="https://github.com/user-attachments/assets/1b03912f-ab7d-4ad9-93df-9c44d3f3ea93" />

```

## Keyboard Shortcuts

| Shortcut | Action |
|---|---|
| `Ctrl+Shift+X` | Snip a screen region |
| `ESC` | Cancel snip |
| `Enter` | Translate manual input |
