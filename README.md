# Manga Translator

A desktop app that extracts Japanese text from manga images using **manga-ocr** and translates it to English.

## Features

- **OCR extraction** – Uses [manga-ocr](https://github.com/kha-white/manga-ocr) to read Japanese text from manga panels
- **Translation** – Translates extracted Japanese text to English via Google Translate
- **Image loading** – Open images from file or paste from clipboard
- **Manual input** – Type any Japanese text and get an instant translation
- **Modern UI** – Built with [customtkinter](https://github.com/TomSchimansky/CustomTkinter)

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

1. Click **Open Image** to load a manga panel or screenshot
2. Click **Extract & Translate** to run OCR and translate
3. Or type Japanese text in the bottom bar and press **Enter**

## Screenshot

```
┌──────────────────────────────────────────────────────────┐
│ [Open Image] [Paste] [Extract & Translate] [Clear]  ✅  │
├──────────────────────────┬───────────────────────────────┤
│                          │ Extracted Japanese Text       │
│                          │ ┌───────────────────────────┐ │
│       Image Preview      │ │ お兄ちゃんどこに行くの?  │ │
│                          │ └───────────────────────────┘ │
│                          │ English Translation           │
│                          │ ┌───────────────────────────┐ │
│                          │ │ Where are you going, bro? │ │
│                          │ └───────────────────────────┘ │
├──────────────────────────┴───────────────────────────────┤
│ Manual input: [________________________] [Translate]     │
└──────────────────────────────────────────────────────────┘
```
